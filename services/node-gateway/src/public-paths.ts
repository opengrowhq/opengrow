// Routes that bypass the gateway's JWT check.
//
// Everything else requires a valid access token at the edge (FastAPI also
// enforces auth — defense in depth). Login is the only public /auth route;
// /auth/me is protected here and re-checked upstream. The first-party tracking
// endpoints are hit by anonymous visitors on customers' published pages, so
// they must stay open.
const PUBLIC_PATHS = new Set<string>([
  '/health',
  '/ready',
  '/auth/login',
  '/analytics/pixel.gif',
  '/analytics/track',
]);

/** True when `pathname` (no query string) may skip gateway auth. */
export function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.has(pathname);
}

/** Strip the query string from a raw request URL. */
export function pathnameOf(url: string): string {
  const q = url.indexOf('?');
  return q === -1 ? url : url.slice(0, q);
}
