import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { trendLabel, trendTone } from "./trend.mjs";

describe("analytics trend", () => {
  it("formats positive deltas with percentages", () => {
    assert.equal(trendLabel({ absolute: 5, percent: 50 }), "+5 (+50%)");
    assert.equal(trendTone({ absolute: 5, percent: 50 }), "up");
  });

  it("formats deltas without a previous baseline", () => {
    assert.equal(trendLabel({ absolute: 10, percent: null }), "+10");
  });

  it("handles flat and negative trends", () => {
    assert.equal(trendLabel({ absolute: 0, percent: 0 }), "No change");
    assert.equal(trendTone({ absolute: 0, percent: 0 }), "flat");
    assert.equal(trendTone({ absolute: -2, percent: -20 }), "down");
  });
});
