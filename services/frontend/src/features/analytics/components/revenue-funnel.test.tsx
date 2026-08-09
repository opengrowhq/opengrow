import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RevenueFunnel } from "./revenue-funnel";

const summary = {
  events: 0,
  visits: 100,
  signups: 10,
  leads: 4,
  customers: 2,
  revenue_cents: 20000,
  currency: "USD",
};

describe("RevenueFunnel", () => {
  it("renders funnel stages", () => {
    render(<RevenueFunnel summary={summary} />);
    expect(screen.getByText(/visits/i)).toBeInTheDocument();
    expect(screen.getByText(/customers/i)).toBeInTheDocument();
  });
  it("renders empty state without summary", () => {
    render(<RevenueFunnel summary={undefined} />);
    expect(screen.getByText(/no funnel/i)).toBeInTheDocument();
  });
});
