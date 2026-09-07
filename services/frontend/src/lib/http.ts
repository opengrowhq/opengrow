// Low-level HTTP transport shared by every feature's api.ts.
// Lite mode talks directly to fastapi-core; production goes via the node-gateway.
import { clearToken, loadRefreshToken, loadToken, saveTokenPair } from "./auth";
import { isAuthEndpoint, shouldRefresh } from "./token-lifecycle.mjs";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
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
// fetch with no Authorization header.

let inflightRefresh: Promise<boolean> | null = null;

/** Refresh the token pair once, sharing one promise across concurrent 401s. */
export function refreshSession(): Promise<boolean> {
  if (!inflightRefresh) {
    inflightRefresh = performRefresh().finally(() => {
      inflightRefresh = null;
    });
  }
  return inflightRefresh;
}

async function performRefresh(): Promise<boolean> {
  const refreshToken = loadRefreshToken();
  if (!refreshToken) return false;
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    return false; // network error — keep the session, surface the original 401
  }
  if (res.status === 401) {
    clearToken();
    redirectToLogin();
    return false;
  }
  if (!res.ok) return false;
  try {
    const pair = (await res.json()) as { access_token: string; refresh_token: string };
    saveTokenPair(pair.access_token, pair.refresh_token);
    return true;
  } catch {
    return false; // malformed success body — keep the session, surface the original 401
  }
}

function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  if (window.location.pathname.startsWith("/login")) return;
  const next = window.location.pathname + window.location.search;
  window.location.assign(`/login?next=${encodeURIComponent(next)}`);
}

/**
 * Run a request; on 401 (except auth endpoints themselves) refresh the token
 * pair and retry the request once with the new token. A retried request that
 * 401s again is returned as-is — the caller's parse() rejects, no loop.
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
  return parse<T>(await withAuthRetry(path, () => fetch(`${API_BASE}${path}`, { headers: authHeaders() })));
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
      headers: authHeaders(),
    }),
  );
  if (!res.ok) await parse(res);
}
