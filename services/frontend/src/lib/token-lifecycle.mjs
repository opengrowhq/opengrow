// Pure helpers for access-token lifetime and refresh decisions.
// Imported by the browser auth glue (lib/http.ts) and exercised directly by
// the node --test suite, so this file stays framework- and DOM-free.

/** Seconds of remaining lifetime below which a token is refreshed proactively. */
export const REFRESH_SKEW_SECONDS = 90;

function decodePayload(segment) {
  const b64 = segment.replace(/-/g, "+").replace(/_/g, "/");
  const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
  return atob(padded);
}

/** JWT `exp` claim in seconds since epoch, or null for malformed/exp-less tokens. */
export function parseJwtExp(token) {
  if (typeof token !== "string") return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const payload = JSON.parse(decodePayload(parts[1]));
    const exp = payload == null ? null : payload.exp;
    return typeof exp === "number" && Number.isFinite(exp) ? exp : null;
  } catch {
    return null;
  }
}

/**
 * Whether to proactively refresh: a refresh token must exist and the access
 * token's exp must be closer than `skewSeconds` to `nowSeconds`.
 * Malformed/exp-less tokens return false — those are left to the 401 path,
 * which retries once after a successful refresh.
 */
export function shouldRefresh(token, refreshToken, nowSeconds, skewSeconds = REFRESH_SKEW_SECONDS) {
  if (!token || !refreshToken) return false;
  const exp = parseJwtExp(token);
  if (exp === null) return false;
  return exp - nowSeconds < skewSeconds;
}

/** True for auth endpoints that must never trigger a refresh/retry loop. */
export function isAuthEndpoint(path) {
  if (typeof path !== "string" || path.length === 0) return false;
  if (/^https?:\/\//.test(path)) {
    try {
      const url = new URL(path);
      return url.pathname === "/auth/login" || url.pathname === "/auth/refresh";
    } catch {
      return false;
    }
  }
  const pathname = path.split("?")[0].split("#")[0];
  return pathname === "/auth/login" || pathname === "/auth/refresh";
}
