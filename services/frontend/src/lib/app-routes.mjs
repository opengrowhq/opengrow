export function tenantSlugOrDemo(slug) {
  const value = typeof slug === "string" ? slug.trim() : "";
  return value || "demo";
}

function routeSegment(value) {
  return encodeURIComponent(String(value).replace(/^\/+|\/+$/g, ""));
}

export function appRootPath(slug) {
  return `/app/${routeSegment(tenantSlugOrDemo(slug))}`;
}

export function appPath(slug, ...segments) {
  const suffix = segments
    .filter((segment) => segment !== undefined && segment !== null && segment !== "")
    .map(routeSegment)
    .join("/");
  return suffix ? `${appRootPath(slug)}/${suffix}` : appRootPath(slug);
}

/**
 * Where to land a user after authentication, given an optional `next` hint
 * (e.g. from `/login?next=onboarding` after checkout). Resolves the special
 * `onboarding` keyword to the tenant-scoped onboarding route, passes through
 * safe in-app paths, and otherwise falls back to the workspace home. Only
 * internal `/app/...` targets are honored, so a crafted `next` cannot become
 * an open redirect.
 */
export function resolvePostAuthPath(next, slug) {
  const value = typeof next === "string" ? next.trim() : "";
  if (value === "onboarding") return appPath(slug, "onboarding");
  if (value.startsWith("/app/") && !value.startsWith("//")) return value;
  return appRootPath(slug);
}
