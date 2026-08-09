export function buildConnectorInput(form) {
  const provider = form.provider === "gsc" ? "gsc" : "ga4";
  const fallbackName = provider === "ga4" ? "GA4" : "Search Console";
  const body = {
    provider,
    display_name: (form.display_name || "").trim() || fallbackName,
  };
  const propertyId = (form.external_property_id || "").trim();
  const siteUrl = (form.site_url || "").trim();
  if (propertyId) body.external_property_id = propertyId;
  if (siteUrl) body.site_url = siteUrl;
  return body;
}
