"use client";
import { StatCard, EmptyState } from "@/components/ui/data-display";
import type { AttributionSummary, AttributionTrend } from "../api";
import { formatRevenue } from "../format.mjs";
import { trendLabel, trendTone } from "../trend.mjs";

function delta(trend: AttributionTrend | undefined, key: string) {
  const d = trend?.deltas?.[key];
  if (!d) return undefined;
  return { value: trendLabel(d), positive: trendTone(d) === "up" };
}

export function KpiSummary({ summary, trend }: { summary?: AttributionSummary; trend?: AttributionTrend }) {
  if (!summary) {
    return <EmptyState title="No attribution data yet" description="Install tracking or import analytics to see revenue by content." />;
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard label="Revenue" value={formatRevenue(summary.revenue_cents, summary.currency)} delta={delta(trend, "revenue_cents")} />
      <StatCard label="Signups" value={summary.signups} delta={delta(trend, "signups")} />
      <StatCard label="Customers" value={summary.customers} delta={delta(trend, "customers")} />
      <StatCard label="Visits" value={summary.visits} delta={delta(trend, "visits")} />
    </div>
  );
}
