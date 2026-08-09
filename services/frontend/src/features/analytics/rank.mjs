export function topAttributionRows(rows, limit = 3) {
  return [...rows]
    .sort((a, b) => {
      const revenue = (b.revenue_cents || 0) - (a.revenue_cents || 0);
      if (revenue) return revenue;
      const customers = (b.customers || 0) - (a.customers || 0);
      if (customers) return customers;
      return (b.events || 0) - (a.events || 0);
    })
    .slice(0, limit);
}
