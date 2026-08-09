import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  trackingStatusDetail,
  trackingStatusLabel,
  trackingStatusTone,
} from "./tracking-status.mjs";

describe("tracking status", () => {
  it("labels missing install state", () => {
    assert.equal(trackingStatusLabel(null), "Not installed");
    assert.equal(trackingStatusDetail(null), "No events yet");
    assert.equal(trackingStatusTone(null), "pending");
  });

  it("summarizes first-party tracking events", () => {
    const status = {
      installed: true,
      events: 5,
      first_party_visits: 3,
      first_party_conversions: 2,
    };

    assert.equal(trackingStatusLabel(status), "Installed");
    assert.equal(trackingStatusDetail(status), "5 events · 3 visits · 2 conversions");
    assert.equal(trackingStatusTone(status), "installed");
  });
});
