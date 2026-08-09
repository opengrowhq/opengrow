import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { NextMoves } from "./next-moves";

const summary = {
  events: 10,
  visits: 50,
  signups: 4,
  leads: 2,
  customers: 0,
  revenue_cents: 0,
  currency: "USD",
};

describe("NextMoves", () => {
  it("surfaces the tracking-install action first when the pixel is missing", () => {
    render(<NextMoves summary={summary} trackingStatus={{ installed: false, events: 0, first_party_visits: 0, first_party_conversions: 0, last_seen_at: null }} />);
    expect(screen.getByText("Install first-party tracking")).toBeInTheDocument();
  });

  it("recommends scaling the winning content and flags the lead-to-customer gap", () => {
    render(
      <NextMoves
        summary={summary}
        trackingStatus={{ installed: true, events: 10, first_party_visits: 40, first_party_conversions: 2, last_seen_at: null }}
        topContent={[{ ...summary, content_piece_id: "cp1", title: "Compounding post", status: "PUBLISHED" }]}
        topChannels={[{ ...summary, channel: "google" }]}
      />,
    );
    expect(screen.getByText("Scale Compounding post")).toBeInTheDocument();
    expect(screen.getByText("Improve lead follow-up")).toBeInTheDocument();
    expect(screen.getByText("Review google")).toBeInTheDocument();
  });

  it("falls back to the first-signal hint when tracking is up but nothing converts", () => {
    render(
      <NextMoves
        summary={{ events: 0, visits: 0, signups: 0, leads: 0, customers: 0, revenue_cents: 0, currency: "USD" }}
        trackingStatus={{ installed: true, events: 0, first_party_visits: 0, first_party_conversions: 0, last_seen_at: null }}
      />,
    );
    expect(screen.getByText("Create the first signal")).toBeInTheDocument();
  });
});
