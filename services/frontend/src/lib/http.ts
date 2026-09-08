// Low-level HTTP transport shared by every feature's api.ts.
// Lite mode talks directly to fastapi-core (Bearer + localStorage); production
// goes via the node-gateway BFF, which moves tokens into httpOnly cookies and
// flags that with the `x-og-auth: cookie` response header.
import {
  clearToken,
  isCookieMode,
  loadRefreshToken,
  loadToken,
  saveTokenPair,
  setCookieMode,
} from "./auth";
import { isAuthEndpoint, shouldRefresh } from "./token-lifecycle.mjs";

// Empty (the default) = same-origin relative calls — required for cookie
// mode, where Caddy routes /auth/* and /api/* to the gateway. Lite deployments
// set NEXT_PUBLIC_API_BASE explicitly (docker-compose.lite.yml uses
// http://localhost:8000).
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** The gateway marks token-stripped (cookie-mode) responses with this header. */
export function readAuthMode(res: Response): void {
  if (res.headers.get("x-og-auth") === "cookie") setCookieMode();
}

export function authHeaders(): Record<string, string> {
  const t = loadToken();
  // Proactive background refresh when the token is about to expire. The
  // current request still goes out with the existing token — if it has
  // already expired, the 401 retry path below picks it up.
  if (t && shouldRefresh(t, loadRefreshToken(), Math.floor(Date.now() / 1000))) {
    void refreshSession();
  }
  return t ? { Authorization: `Bearer ${t}` } : {};
}

// ------------------------------ Token refresh ------------------------------
// POST /auth/refresh is unauthenticated in the gateway, so this is a plain
// fetch with no Authorization header. In cookie mode the refresh token rides
// as the og_rt httpOnly cookie (the gateway injects it into the body for
// fastapi-core), so no body is needed from JS.

let inflightRefresh: Promise<boolean> | null = null;

/** Refresh the session once, sharing one promise across concurrent 401s. */
export function refreshSession(): Promise<boolean> {
  if (!inflightRefresh) {
    inflightRefresh = performRefresh().finally(() => {
      inflightRefresh = null;
    });
  }
  return inflightRefresh;
}

async function performRefresh(): Promise<boolean> {
  // Always attempt: in lite mode the stored refresh token goes in the body; in
  // cookie mode the og_rt httpOnly cookie rides along and the gateway injects
  // it for fastapi-core. We cannot know which transport applies until the
  // response tells us (x-og-auth header), and a wrong guess the other way
  // would break cookie-mode session restore after a page reload.
  const refreshToken = loadRefreshToken();
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(refreshToken ? { refresh_token: refreshToken } : {}),
    });
  } catch {
    return false; // network error — keep the session, surface the original 401
  }
  readAuthMode(res);
  if (res.status === 401) {
    // Session is dead under either transport. Cookie mode: clear the orphan
    // cookies at the BFF (localStorage is already empty there).
    if (isCookieMode()) {
      void fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" }).catch(
        () => {},
      );
    } else {
      clearToken();
    }
    redirectToLogin();
    return false;
  }
  if (!res.ok) return false;
  if (isCookieMode()) {
    return true; // body stripped by the gateway; cookies rotated in place
  }
  try {
    const pair = (await res.json()) as { access_token: string; refresh_token: string };
    saveTokenPair(pair.access_token, pair.refresh_token);
    return true;
  } catch {
    return false; // malformed success body — keep the session, surface the original 401
  }
}

let ensureSessionTried = false;

/**
 * Cookie-mode session restore after a page reload: no token is in
 * localStorage, but the og_rt cookie may still be valid. A silent refresh
 * succeeds only when the gateway accepts that cookie. No-op (returns false)
 * in lite mode, where nothing can restore the session.
 */
export async function ensureSession(): Promise<boolean> {
  if (typeof window === "undefined") return false;
  if (loadToken() || isCookieMode()) return true;
  if (ensureSessionTried) return isCookieMode();
  ensureSessionTried = true;
  return refreshSession();
}

/** Sign out under both transports: localStorage plus, in cookie mode, the BFF cookies. */
export function logout(): void {
  if (isCookieMode()) {
    void fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" }).catch(
      () => {},
    );
  }
  clearToken();
}

function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  if (window.location.pathname.startsWith("/login")) return;
  const next = window.location.pathname + window.location.search;
  window.location.assign(`/login?next=${encodeURIComponent(next)}`);
}

/**
 * Run a request; on 401 (except auth endpoints themselves) refresh the
 * session and retry the request once with the new token. A retried request
 * that 401s again is returned as-is — the caller's parse() rejects, no loop.
 */
async function withAuthRetry(
  path: string,
  doFetch: () => Promise<Response>,
): Promise<Response> {
  const res = await doFetch();
  if (res.status !== 401 || isAuthEndpoint(path)) return res;
  if (!(await refreshSession())) return res;
  return doFetch();
}

export async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  return parse<T>(
    await withAuthRetry(path, () =>
      fetch(`${API_BASE}${path}`, { credentials: "include", headers: authHeaders() }),
    ),
  );
}

export async function apiSend<T>(
  path: string,
  method: "POST" | "PATCH" | "DELETE",
  body?: unknown,
): Promise<T> {
  return parse<T>(
    await withAuthRetry(path, () =>
      fetch(`${API_BASE}${path}`, {
        method,
        credentials: "include",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      }),
    ),
  );
}

// DELETE endpoints that return 204 No Content would break `parse` (empty body),
// so they get a dedicated helper that only surfaces errors.
export async function apiDelete(path: string): Promise<void> {
  const res = await withAuthRetry(path, () =>
    fetch(`${API_BASE}${path}`, {
      method: "DELETE",
      credentials: "include",
      headers: authHeaders(),
    }),
  );
  if (!res.ok) await parse(res);
}
