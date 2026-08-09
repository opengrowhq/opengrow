import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { cleanImportRow, dollarsToCents } from "./import-form.mjs";

describe("analytics import form", () => {
  it("converts dollar input to cents", () => {
    assert.equal(dollarsToCents("123.45"), 12345);
    assert.equal(dollarsToCents("0"), 0);
    assert.equal(dollarsToCents("bad"), 0);
  });

  it("cleans empty fields and keeps positive counts", () => {
    assert.deepEqual(
      cleanImportRow({
        content_piece_id: " page-1 ",
        source_url: " https://example.test/demo ",
        channel: "Paid Search",
        visits: "12",
        signups: "",
        leads: "2",
        customers: "0",
        revenue: "19.99",
        currency: "eur",
      }),
      {
        content_piece_id: "page-1",
        source_url: "https://example.test/demo",
        channel: "paid_search",
        visits: 12,
        leads: 2,
        revenue_cents: 1999,
        currency: "EUR",
      },
    );
  });
});
