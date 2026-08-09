import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KpiSummary } from "./kpi-summary";
import { trendLabel } from "../trend.mjs";
import type { AttributionTrend } from "../api";

const summary = { events: 10, visits: 100, signups: 8, leads: 3, customers: 2, revenue_cents: 12900, currency: "USD" };

const trend: AttributionTrend = {
  days: 30,
  current: summary,
  previous: { events: 8, visits: 90, signups: 6, leads: 2, customers: 1, revenue_cents: 12400, currency: "USD" },
  deltas: {
    revenue_cents: { absolute: 500, percent: 12 },
    visits: { absolute: 10, percent: 5 },
  },
};

describe("KpiSummary", () => {
  it("renders revenue and visit KPIs", () => {
    render(<KpiSummary summary={summary} trend={undefined} />);
    expect(screen.getByText(/revenue/i)).toBeInTheDocument();
    expect(screen.getByText("$129")).toBeInTheDocument();
    expect(screen.getByText(/visits/i)).toBeInTheDocument();
  });
  it("renders an empty state when there is no summary", () => {
    render(<KpiSummary summary={undefined} trend={undefined} />);
    expect(screen.getByText(/no attribution data/i)).toBeInTheDocument();
  });
  it("renders the revenue delta with positive/up styling when trend has deltas", () => {
    render(<KpiSummary summary={summary} trend={trend} />);
    const label = trendLabel(trend.deltas.revenue_cents);
    const deltaEl = screen.getByText(label);
    expect(deltaEl).toBeInTheDocument();
    // emerald-700 (5.37:1 on white), not emerald-600 (3.67:1) — this is text-xs
    // and must clear the 4.5:1 minimum.
    expect(deltaEl).toHaveClass("text-emerald-700");
  });
});
