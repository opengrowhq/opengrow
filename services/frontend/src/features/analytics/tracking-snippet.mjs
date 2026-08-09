export function trackingPixelUrl(apiBase, tenantSlug, contentPieceId) {
  const base = String(apiBase || "").replace(/\/+$/, "");
  const params = new URLSearchParams({ tenant: tenantSlug });
  if (contentPieceId) params.set("content_piece_id", contentPieceId);
  return `${base}/analytics/pixel.gif?${params.toString()}`;
}

export function trackingPixelSnippet(apiBase, tenantSlug, contentPieceId) {
  const src = trackingPixelUrl(apiBase, tenantSlug, contentPieceId);
  return `<img src="${src}" width="1" height="1" alt="" referrerpolicy="no-referrer-when-downgrade" />`;
}

export function conversionFetchSnippet(
  apiBase,
  tenantSlug,
  contentPieceId,
  eventType = "lead",
) {
  const base = String(apiBase || "").replace(/\/+$/, "");
  const normalizedEvent = ["signup", "lead", "customer", "revenue"].includes(eventType)
    ? eventType
    : "lead";
  const body = {
    tenant_slug: tenantSlug,
    event_type: normalizedEvent,
    ...(contentPieceId ? { content_piece_id: contentPieceId } : {}),
    source_url: "https://example.com/landing-page",
    external_id: "lead-or-order-id",
    ...(normalizedEvent === "revenue" ? { amount_cents: 4900, currency: "USD" } : {}),
  };
  return [
    `fetch("${base}/analytics/track", {`,
    '  method: "POST",',
    '  headers: { "Content-Type": "application/json" },',
    `  body: JSON.stringify(${JSON.stringify(body, null, 2).replace(/\n/g, "\n  ")}),`,
    "});",
  ].join("\n");
}
