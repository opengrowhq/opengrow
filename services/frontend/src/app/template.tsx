// App Router template: re-mounts on every navigation, giving each route a
// gentle fade-in. Opacity-only on purpose — a transform would create a
// containing block and drag the fixed app sidebar during the animation.
//
// The fade is CSS rather than JS because `useReducedMotion()` reports false
// during SSR and its real value only after hydration. Branching on it here
// changed the rendered tree between server and client, so every route threw a
// hydration mismatch for anyone with "Reduce Motion" enabled. A CSS animation
// emits identical markup either way, and the global `prefers-reduced-motion`
// rule in globals.css already collapses its duration.

export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="route-fade">{children}</div>;
}
