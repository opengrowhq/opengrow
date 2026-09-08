// Routes that bypass the gateway's JWT check.
//
// Everything else requires a valid access token at the edge (FastAPI also
// enforces auth — defense in depth). Login, token refresh, and invite
// acceptance are the public /auth + /invites routes — /auth/me and every
// other /invites route are protected here and re-checked upstream. The local
// BFF routes /auth/logout and /auth/session are public by design (logout is
// idempotent; /auth/session is fixation-guarded, see routes/auth.ts). The
// first-party tracking endpoints are hit by anonymous visitors on customers'
// published pages, so they must stay open. Billing webhooks are called by
// provider services (Paddle/Stripe/…) with no user token of their own.
const PUBLIC_PATHS = new Set<string>([
  "/health",
  "/ready",
  "/auth/login",
  "/auth/refresh",
  // Local BFF routes (see routes/auth.ts) — not proxied.
  "/auth/logout",
  "/auth/session",
  "/analytics/pixel.gif",
  "/analytics/track",
  // Legacy billing webhook (hosted billing overlay).
  "/billing/webhook",
]);

// Public path shapes with a dynamic segment (exact paths live in PUBLIC_PATHS).
const PUBLIC_PATTERNS: RegExp[] = [
  // POST /invites/{token}/accept — invite acceptance is a pre-auth login-like
  // flow that returns a token pair.
  /^\/invites\/[^/]+\/accept$/,
  // POST /billing/webhook/{provider} — provider-signed webhooks carry no
  // user token; signature verification happens upstream.
  /^\/billing\/webhook\/[^/]+$/,
];

// API namespaces proxied 1:1 to fastapi-core (same paths the frontend/lite use).
// Keep in sync with the API prefixes called by the frontend
// (services/frontend/src/features/*/api.ts); public-paths.test.ts asserts this.
export const PROXIED_PREFIXES = [
  "/auth",
  "/assets",
  "/generations",
  "/content",
  "/brands",
  "/analytics",
  "/invites",
  "/playbooks",
  "/orchestrator",
  // Hosted billing overlay APIs — proxied 1:1; all /billing routes stay
  // edge-auth protected except the webhook paths above.
  "/billing",
];

/** True when `pathname` (no query string) may skip gateway auth. */
export function isPublicPath(pathname: string): boolean {
  return (
    PUBLIC_PATHS.has(pathname) ||
    PUBLIC_PATTERNS.some((re) => re.test(pathname))
  );
}

/** Strip the query string from a raw request URL. */
export function pathnameOf(url: string): string {
  const q = url.indexOf("?");
  return q === -1 ? url : url.slice(0, q);
}
