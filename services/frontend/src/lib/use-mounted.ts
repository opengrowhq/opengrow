"use client";

import { useSyncExternalStore } from "react";

// The store never changes after hydration, so subscribing is a no-op.
const emptySubscribe = () => () => {};

/**
 * Returns false during SSR and the first client render, then true once the
 * client has hydrated. Built on useSyncExternalStore so the first client
 * render uses the server snapshot (false) and matches the server HTML, then
 * re-renders to true — the hydration-safe way to gate browser-only state
 * (auth token in localStorage, react-query results enabled by that token).
 * See `@/lib/first-paint` for why this prevents hydration mismatches.
 */
export function useMounted(): boolean {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
}
