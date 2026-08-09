function toInt(value) {
  const parsed = Number.parseInt(String(value || "0"), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

export function dollarsToCents(value) {
  const parsed = Number.parseFloat(String(value || "0"));
  return Number.isFinite(parsed) && parsed > 0 ? Math.round(parsed * 100) : 0;
}

export function cleanImportRow(form) {
  const row = {
    currency: (form.currency || "USD").trim().toUpperCase(),
  };
  const contentPieceId = (form.content_piece_id || "").trim();
  const sourceUrl = (form.source_url || "").trim();
  const channel = (form.channel || "").trim().toLowerCase().replace(/\s+/g, "_");
  const visits = toInt(form.visits);
  const signups = toInt(form.signups);
  const leads = toInt(form.leads);
  const customers = toInt(form.customers);
  const revenueCents = dollarsToCents(form.revenue);

  if (contentPieceId) row.content_piece_id = contentPieceId;
  if (sourceUrl) row.source_url = sourceUrl;
  if (channel) row.channel = channel;
  if (visits) row.visits = visits;
  if (signups) row.signups = signups;
  if (leads) row.leads = leads;
  if (customers) row.customers = customers;
  if (revenueCents) row.revenue_cents = revenueCents;

  return row;
}
