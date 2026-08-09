import { describe, it, expect, afterEach, vi } from "vitest";
import { render } from "@testing-library/react";
import Template from "./template";

// The bug this pins: the template used to branch on `useReducedMotion()`, which
// reports false during SSR and its real value only after hydration. With
// "Reduce Motion" on, the server emitted <motion.div style="opacity:0"> where
// the client emitted a bare fragment, so React threw a hydration mismatch on
// every route.
//
// The invariant that prevents it is that the markup must not depend on the
// reduced-motion setting at all. These tests assert exactly that, so a future
// change reintroducing a JS branch fails here.

function withReducedMotion(reduce: boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: reduce && query.includes("prefers-reduced-motion"),
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

afterEach(() => {
  Reflect.deleteProperty(window, "matchMedia");
});

describe("route template", () => {
  it("never consults the reduced-motion media query while rendering", () => {
    // The root cause, asserted directly: if rendering reads matchMedia, the
    // output can differ between server and client, which is the mismatch. Not
    // reading it at all makes the markup provably setting-independent.
    // Comparing two rendered outputs would NOT catch this — motion's hook does
    // not observe an injected matchMedia stub under jsdom, so such a test
    // passes even against the broken implementation.
    withReducedMotion(false);
    const spy = vi.spyOn(window, "matchMedia");

    render(<Template>content</Template>);

    const motionQueries = spy.mock.calls
      .map(([q]) => String(q))
      .filter((q) => q.includes("prefers-reduced-motion"));
    expect(motionQueries).toEqual([]);
  });

  it("hands the fade to CSS so the duration collapses under reduced motion", () => {
    withReducedMotion(true);
    const { container } = render(<Template>content</Template>);
    const wrapper = container.firstElementChild;

    expect(wrapper).toHaveClass("route-fade");
    // An inline opacity is the signature of the JS approach that caused the
    // mismatch — the CSS class must carry the animation instead.
    expect(wrapper?.getAttribute("style")).toBeNull();
  });

  it("renders its children", () => {
    withReducedMotion(false);
    const { container } = render(<Template>content</Template>);
    expect(container.textContent).toBe("content");
  });
});
