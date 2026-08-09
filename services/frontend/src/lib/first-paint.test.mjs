import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { firstPaintLoading, listViewState } from "./first-paint.mjs";

describe("first-paint helpers", () => {
  it("forces loading before mount regardless of isLoading", () => {
    // The invariant that prevents the hydration mismatch: the server and the
    // first client render (both mounted === false) must agree, so first paint
    // is always the loading state even when the query already reports settled.
    assert.equal(firstPaintLoading(false, false), true);
    assert.equal(firstPaintLoading(false, true), true);
  });

  it("defers to isLoading once mounted", () => {
    assert.equal(firstPaintLoading(true, true), true);
    assert.equal(firstPaintLoading(true, false), false);
  });

  it("listViewState is loading on the server / first paint", () => {
    assert.equal(listViewState({ mounted: false, isLoading: false, count: 0 }), "loading");
    assert.equal(listViewState({ mounted: false, isLoading: false, count: 5 }), "loading");
  });

  it("listViewState resolves empty vs list only after mount", () => {
    assert.equal(listViewState({ mounted: true, isLoading: true, count: 0 }), "loading");
    assert.equal(listViewState({ mounted: true, isLoading: false, count: 0 }), "empty");
    assert.equal(listViewState({ mounted: true, isLoading: false, count: 3 }), "list");
  });
});
