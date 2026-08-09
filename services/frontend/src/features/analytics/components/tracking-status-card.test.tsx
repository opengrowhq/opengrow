import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TrackingStatusCard } from "./tracking-status-card";

describe("TrackingStatusCard", () => {
  it("shows installed state", () => {
    render(
      <TrackingStatusCard
        status={{
          installed: true,
          events: 5,
          first_party_visits: 5,
          first_party_conversions: 1,
          last_seen_at: "2026-07-01T00:00:00Z",
        }}
        tenantSlug="demo"
      />,
    );
    expect(screen.getByText(/tracking/i)).toBeInTheDocument();
  });

  it("shows not-installed guidance", () => {
    render(
      <TrackingStatusCard
        status={{
          installed: false,
          events: 0,
          first_party_visits: 0,
          first_party_conversions: 0,
          last_seen_at: null,
        }}
        tenantSlug="demo"
      />,
    );
    expect(screen.getByText(/snippet|install/i)).toBeInTheDocument();
  });
});
