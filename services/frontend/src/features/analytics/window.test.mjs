import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  analyticsWindowLabel,
  analyticsWindowQuery,
  analyticsWindows,
} from "./window.mjs";

describe("analytics window", () => {
  it("lists dashboard windows", () => {
    assert.deepEqual(analyticsWindows, ["7", "30", "90", "all"]);
  });

  it("formats window labels", () => {
    assert.equal(analyticsWindowLabel("30"), "30d");
    assert.equal(analyticsWindowLabel("all"), "All");
  });

  it("builds safe query strings", () => {
    assert.equal(analyticsWindowQuery("7"), "?days=7");
    assert.equal(analyticsWindowQuery("all"), "");
    assert.equal(analyticsWindowQuery("bad"), "");
    assert.equal(analyticsWindowQuery("500"), "");
  });
});
