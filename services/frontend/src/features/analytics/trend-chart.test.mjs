import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  channelTrendChartRows,
  compactTrendChartRows,
  trendBarWidth,
  trendChartRows,
} from "./trend-chart.mjs";

describe("analytics trend chart", () => {
  it("keeps empty bars at zero", () => {
    assert.equal(trendBarWidth(0, 10), 0);
    assert.equal(trendBarWidth(10, 0), 0);
  });

  it("keeps visible non-zero bars", () => {
    assert.equal(trendBarWidth(1, 100), 4);
    assert.equal(trendBarWidth(50, 100), 50);
  });

  it("builds current and previous chart rows", () => {
    const rows = trendChartRows({
      current: { visits: 100, leads: 20, customers: 5, revenue_cents: 10000 },
      previous: { visits: 50, leads: 40, customers: 0, revenue_cents: 5000 },
    });

    assert.equal(rows[0].label, "Visits");
    assert.equal(rows[0].currentWidth, 100);
    assert.equal(rows[0].previousWidth, 50);
    assert.equal(rows[1].currentWidth, 50);
    assert.equal(rows[1].previousWidth, 100);
  });

  it("builds compact channel chart rows", () => {
    const rows = compactTrendChartRows({
      current: { visits: 12, leads: 3, customers: 1 },
      previous: { visits: 6, leads: 6, customers: 0 },
    });

    assert.deepEqual(
      rows.map((row) => row.metric),
      ["visits", "leads", "customers"],
    );
    assert.equal(rows[2].currentWidth, 100);
    assert.equal(rows[2].previousWidth, 0);
  });

  it("keeps the channel helper alias stable", () => {
    assert.equal(channelTrendChartRows, compactTrendChartRows);
  });
});
