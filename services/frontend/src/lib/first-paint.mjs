// First-paint helpers for auth-gated client pages.
//
// These pages are "use client" but still server-rendered. Their react-query
// hooks are enabled only when a token exists, and the token lives in
// localStorage — absent on the server, present on the client. That makes
// `isLoading` differ between the server render (false → empty/data) and the
// first client render (true → loading), which React reports as a hydration
// mismatch.
//
// The fix: treat "not yet mounted on the client" as loading. The server and
// the first client render both see `mounted === false`, so both render the
// same loading state; real data-driven state only takes over after mount.

/** True when a data-dependent view should render its loading state.
 *  Always true before the client has mounted, so first paint is deterministic. */
export function firstPaintLoading(mounted, isLoading) {
  return !mounted || Boolean(isLoading);
}

/** Tri-state for a simple auth-gated list view. */
export function listViewState({ mounted, isLoading, count }) {
  if (firstPaintLoading(mounted, isLoading)) return "loading";
  if (!count) return "empty";
  return "list";
}
