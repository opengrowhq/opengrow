import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { attributionRecommendations } from "./recommendations.mjs";

describe("attribution recommendations", () => {
  it("prioritizes tracking install when no signal exists", () => {
    const [first] = attributionRecommendations({
      summary: {},
      trackingStatus: { installed: false },
    });

    assert.equal(first.title, "Install first-party tracking");
    assert.equal(first.tone, "urgent");
  });

  it("recommends scaling winning content and fixing conversion gaps", () => {
    const recommendations = attributionRecommendations({
      summary: { visits: 100, leads: 0, customers: 0, revenue_cents: 0 },
      topContent: [{ title: "Demo launch", events: 25, leads: 0, customers: 0 }],
      topChannels: [{ channel: "organic_search", visits: 100, leads: 0, customers: 0, events: 25 }],
      trackingStatus: { installed: true },
    });

    assert.equal(recommendations[0].title, "Scale Demo launch");
    assert.equal(recommendations[1].title, "Tighten the page offer");
    assert.equal(recommendations[2].title, "Review organic search");
  });
});
