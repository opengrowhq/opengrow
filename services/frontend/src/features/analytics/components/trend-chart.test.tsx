import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TrendChart } from "./trend-chart";

const trend = {
  days: 30,
  current: { events: 0, visits: 50, signups: 4, leads: 1, customers: 1, revenue_cents: 5000, currency: "USD" },
  previous: { events: 0, visits: 25, signups: 2, leads: 0, customers: 0, revenue_cents: 0, currency: "USD" },
  deltas: {},
};

describe("TrendChart", () => {
  it("renders current and previous legend", () => {
    render(<TrendChart trend={trend} currency="USD" />);
    expect(screen.getByText(/current/i)).toBeInTheDocument();
    expect(screen.getByText(/previous/i)).toBeInTheDocument();
  });
  it("renders empty state without a trend", () => {
    render(<TrendChart trend={undefined} currency="USD" />);
    expect(screen.getByText(/no trend/i)).toBeInTheDocument();
  });
});
