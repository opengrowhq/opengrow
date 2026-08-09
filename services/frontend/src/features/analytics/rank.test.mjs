import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { topAttributionRows } from "./rank.mjs";

describe("analytics ranking", () => {
  it("sorts by revenue, customers, then events", () => {
    const rows = topAttributionRows([
      { title: "Events", revenue_cents: 0, customers: 0, events: 10 },
      { title: "Customers", revenue_cents: 0, customers: 2, events: 2 },
      { title: "Revenue", revenue_cents: 100, customers: 0, events: 1 },
    ]);

    assert.deepEqual(rows.map((row) => row.title), [
      "Revenue",
      "Customers",
      "Events",
    ]);
  });
});
