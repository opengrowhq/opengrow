import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { formatRevenue } from "./format.mjs";

describe("analytics formatters", () => {
  it("formats cents as whole currency", () => {
    assert.equal(formatRevenue(123456, "USD"), "$1,235");
  });

  it("handles missing revenue as zero", () => {
    assert.equal(formatRevenue(undefined, "USD"), "$0");
  });
});
