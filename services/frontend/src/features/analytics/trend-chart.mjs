const metricLabels = {
  visits: "Visits",
  leads: "Leads",
  customers: "Customers",
  revenue_cents: "Revenue",
};

export function trendBarWidth(value, max) {
  const numericValue = Number(value || 0);
  const numericMax = Number(max || 0);
  if (numericValue <= 0 || numericMax <= 0) return 0;
  return Math.max(4, Math.round((numericValue / numericMax) * 100));
}

export function trendChartRows(trend, metrics = Object.keys(metricLabels)) {
  return metrics.map((metric) => {
    const current = Number(trend?.current?.[metric] ?? 0);
    const previous = Number(trend?.previous?.[metric] ?? 0);
    const max = Math.max(current, previous);
    return {
      metric,
      label: metricLabels[metric] ?? metric,
      current,
      previous,
      currentWidth: trendBarWidth(current, max),
      previousWidth: trendBarWidth(previous, max),
    };
  });
}

export function compactTrendChartRows(trend) {
  return trendChartRows(trend, ["visits", "leads", "customers"]);
}

export const channelTrendChartRows = compactTrendChartRows;
