import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildConnectorInput } from "./connector-form.mjs";

describe("analytics connector form", () => {
  it("builds a GA4 connector payload", () => {
    assert.deepEqual(
      buildConnectorInput({
        provider: "ga4",
        display_name: " Main property ",
        external_property_id: " 123456 ",
      }),
      {
        provider: "ga4",
        display_name: "Main property",
        external_property_id: "123456",
      },
    );
  });

  it("defaults names and ignores blank fields", () => {
    assert.deepEqual(
      buildConnectorInput({
        provider: "gsc",
        display_name: "",
        site_url: " https://example.test ",
      }),
      {
        provider: "gsc",
        display_name: "Search Console",
        site_url: "https://example.test",
      },
    );
  });
});
