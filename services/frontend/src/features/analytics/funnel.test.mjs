import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { attributionFunnel, percent, revenuePerCustomer } from "./funnel.mjs";

describe("attribution funnel", () => {
  it("formats empty rates safely", () => {
    assert.equal(percent(1, 0), "0%");
    assert.equal(revenuePerCustomer(10000, 0), 0);
  });

  it("calculates executive conversion metrics", () => {
    const funnel = attributionFunnel({
      visits: 100,
      leads: 25,
      customers: 5,
      revenue_cents: 50000,
    });

    assert.equal(funnel.visitor_to_lead, "25%");
    assert.equal(funnel.lead_to_customer, "20%");
    assert.equal(funnel.revenue_per_customer_cents, 10000);
  });
});
