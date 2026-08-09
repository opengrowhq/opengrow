export function percent(numerator, denominator) {
  if (!denominator) return "0%";
  return `${Math.round((Number(numerator || 0) / Number(denominator)) * 100)}%`;
}

export function revenuePerCustomer(cents, customers) {
  if (!customers) return 0;
  return Math.round(Number(cents || 0) / Number(customers));
}

export function attributionFunnel(summary) {
  const visits = Number(summary?.visits ?? 0);
  const leads = Number(summary?.leads ?? 0);
  const customers = Number(summary?.customers ?? 0);
  const revenue = Number(summary?.revenue_cents ?? 0);
  return {
    visitor_to_lead: percent(leads, visits),
    lead_to_customer: percent(customers, leads),
    revenue_per_customer_cents: revenuePerCustomer(revenue, customers),
  };
}
