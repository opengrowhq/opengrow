import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BreakdownTable } from "./breakdown-table";

const rows = [
  { channel: "github", visits: 40, signups: 3, leads: 1, customers: 1, revenue_cents: 9000, currency: "USD", events: 0 },
  { channel: "email", visits: 10, signups: 1, leads: 0, customers: 0, revenue_cents: 0, currency: "USD", events: 0 },
];

describe("BreakdownTable", () => {
  it("renders ranked rows by label", () => {
    render(
      <BreakdownTable
        rows={rows}
        label={(r) => r.channel}
        columns={[{ key: "visits", label: "Visits", render: (r) => r.visits }]}
      />,
    );
    expect(screen.getByText("github")).toBeInTheDocument();
    expect(screen.getByText("email")).toBeInTheDocument();
    expect(screen.getByText("Visits")).toBeInTheDocument();
  });

  it("renders empty state for no rows", () => {
    render(<BreakdownTable rows={[]} label={() => ""} columns={[]} />);
    expect(screen.getByText(/nothing to show/i)).toBeInTheDocument();
  });
});
