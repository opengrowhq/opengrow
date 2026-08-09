import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  conversionFetchSnippet,
  trackingPixelSnippet,
  trackingPixelUrl,
} from "./tracking-snippet.mjs";

describe("tracking snippet", () => {
  it("builds a tenant tracking pixel url", () => {
    assert.equal(
      trackingPixelUrl("http://localhost:8000/", "demo", "content-1"),
      "http://localhost:8000/analytics/pixel.gif?tenant=demo&content_piece_id=content-1",
    );
  });

  it("builds an embeddable 1x1 image snippet", () => {
    assert.equal(
      trackingPixelSnippet("http://localhost:8000", "demo"),
      '<img src="http://localhost:8000/analytics/pixel.gif?tenant=demo" width="1" height="1" alt="" referrerpolicy="no-referrer-when-downgrade" />',
    );
  });

  it("builds a conversion fetch snippet", () => {
    const snippet = conversionFetchSnippet(
      "http://localhost:8000/",
      "demo",
      "content-1",
    );

    assert.ok(snippet.includes("http://localhost:8000/analytics/track"));
    assert.ok(snippet.includes('"tenant_slug": "demo"'));
    assert.ok(snippet.includes('"content_piece_id": "content-1"'));
    assert.ok(snippet.includes('"event_type": "lead"'));
  });

  it("builds revenue conversion examples", () => {
    const snippet = conversionFetchSnippet(
      "http://localhost:8000/",
      "demo",
      "content-1",
      "revenue",
    );

    assert.ok(snippet.includes('"event_type": "revenue"'));
    assert.ok(snippet.includes('"amount_cents": 4900'));
    assert.ok(snippet.includes('"currency": "USD"'));
  });
});
