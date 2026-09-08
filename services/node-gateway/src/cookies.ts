// Cookie-mode auth helpers (pure functions — unit-tested in cookies.test.ts).
//
// In gateway deployments the BFF moves JWTs out of browser storage: login,
// refresh, set-password, and invite-accept responses are intercepted on the
// way out (tokens stripped from the JSON body, Set-Cookie headers added), and
// the access token is re-injected from the httpOnly cookie into the
// Authorization header on the way in. Lite mode (no gateway) keeps Bearer +
// localStorage and never touches any of this.
import { decodeJwt } from "jose";

export const SESSION_COOKIE = "og_at";
export const REFRESH_COOKIE = "og_rt";

const INTERCEPTED_PATHS = new Set([
  "/auth/login",
  "/auth/refresh",
  // Hosted-only core route; its responses flow through the /auth proxy.
  "/auth/set-password",
]);
const INVITE_ACCEPT = /^\/invites\/[^/]+\/accept$/;

/** True for token-issuing endpoints whose JSON body the gateway rewrites. */
export function shouldIntercept(pathname: string, method: string): boolean {
  if (method !== "POST") return false;
  return INTERCEPTED_PATHS.has(pathname) || INVITE_ACCEPT.test(pathname);
}

// Cookie values land in a header, so refuse anything outside the JWT
// base64url alphabet rather than risk header injection.
const TOKEN_RE = /^[A-Za-z0-9\-._]+$/;

/** maxAge (seconds) from the JWT `exp` claim; null when it can't be read. */
function maxAgeFromExp(token: string, nowSec: number): number | null {
  try {
    const { exp } = decodeJwt(token); // decode only — verification stays at the edge
    if (typeof exp !== "number" || !Number.isFinite(exp)) return null;
    return Math.max(0, exp - nowSec);
  } catch {
    return null; // malformed token → session cookie (no maxAge)
  }
}

/**
 * Build Set-Cookie header values for a token pair.
 * og_at is scoped to `/` (sent on every API call); og_rt to `/auth` (only
 * login/refresh/session see it). Both HttpOnly + SameSite=Strict.
 */
export function buildSessionCookies(
  pair: { access_token: string; refresh_token?: string | null },
  opts: { secure: boolean; nowSec?: number },
): string[] {
  const nowSec = opts.nowSec ?? Math.floor(Date.now() / 1000);
  const secure = opts.secure ? "; Secure" : "";
  const cookies: string[] = [];

  if (TOKEN_RE.test(pair.access_token)) {
    const maxAge = maxAgeFromExp(pair.access_token, nowSec);
    cookies.push(
      `${SESSION_COOKIE}=${pair.access_token}; Path=/; HttpOnly; SameSite=Strict` +
        (maxAge !== null ? `; Max-Age=${maxAge}` : "") +
        secure,
    );
  }

  const refresh = pair.refresh_token;
  if (
    typeof refresh === "string" &&
    refresh.length > 0 &&
    TOKEN_RE.test(refresh)
  ) {
    const maxAge = maxAgeFromExp(refresh, nowSec);
    cookies.push(
      `${REFRESH_COOKIE}=${refresh}; Path=/auth; HttpOnly; SameSite=Strict` +
        (maxAge !== null ? `; Max-Age=${maxAge}` : "") +
        secure,
    );
  }

  return cookies;
}

/** Remove token fields from a token-pair-shaped JSON body (shallow copy). */
export function stripTokenPair(body: unknown): {
  stripped: unknown;
  hadTokens: boolean;
} {
  if (
    typeof body === "object" &&
    body !== null &&
    !Array.isArray(body) &&
    typeof (body as Record<string, unknown>).access_token === "string"
  ) {
    const rest = { ...(body as Record<string, unknown>) };
    delete rest.access_token;
    delete rest.refresh_token;
    return { stripped: rest, hadTokens: true };
  }
  return { stripped: body, hadTokens: false };
}

/** Read one cookie value from a raw `cookie` request header. */
export function readCookieValue(
  cookieHeader: string | undefined,
  name: string,
): string | null {
  if (!cookieHeader) return null;
  for (const part of cookieHeader.split(";")) {
    const eq = part.indexOf("=");
    if (eq === -1) continue;
    if (part.slice(0, eq).trim() !== name) continue;
    const raw = part.slice(eq + 1).trim();
    try {
      return decodeURIComponent(raw);
    } catch {
      return raw; // malformed %-escape — the token check downstream will reject it
    }
  }
  return null;
}

interface HeaderBag {
  headers: Record<string, unknown>;
}

/**
 * Re-inject the session cookie as a Bearer Authorization header so the edge
 * JWT check works unchanged. Mutates `request.headers`; returns true when it
 * injected. Never overrides an existing Authorization header.
 */
export function applyCookieAuth(request: HeaderBag): boolean {
  const existing =
    request.headers.authorization ?? request.headers.Authorization;
  if (typeof existing === "string" && existing.length > 0) return false;
  const token = readCookieValue(
    request.headers.cookie as string | undefined,
    SESSION_COOKIE,
  );
  if (!token) return false;
  request.headers.authorization = `Bearer ${token}`;
  return true;
}

export interface RewriteResult {
  payload: string;
  setCookies: string[];
  modeHeader: boolean;
}

/**
 * Decide whether a proxied response carries a token pair to move into cookies.
 * Pure: the onSend hook is a thin adapter over this. Returns null when nothing
 * should change (non-intercepted path, non-2xx, non-JSON, unparseable body,
 * or no tokens present) — callers pass the original payload through.
 */
export function maybeRewriteAuthResponse(input: {
  pathname: string;
  method: string;
  statusCode: number;
  contentType: string | undefined;
  payload: string | Buffer;
  secure: boolean;
  nowSec?: number;
}): RewriteResult | null {
  if (!shouldIntercept(input.pathname, input.method)) return null;
  if (input.statusCode < 200 || input.statusCode >= 300) return null;
  if (!(input.contentType ?? "").includes("application/json")) return null;

  const raw = Buffer.isBuffer(input.payload)
    ? input.payload.toString("utf8")
    : input.payload;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }

  const { stripped, hadTokens } = stripTokenPair(parsed);
  if (!hadTokens) return null;

  return {
    payload: JSON.stringify(stripped),
    setCookies: buildSessionCookies(
      parsed as { access_token: string; refresh_token?: string | null },
      { secure: input.secure, nowSec: input.nowSec },
    ),
    modeHeader: true,
  };
}
