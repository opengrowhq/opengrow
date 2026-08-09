"use client";
import { EmptyState } from "@/components/ui/data-display";
import type { AttributionSummary } from "../api";
import { formatRevenue } from "../format.mjs";
import { attributionFunnel } from "../funnel.mjs";

export function RevenueFunnel({ summary }: { summary?: AttributionSummary }) {
  if (!summary) {
    return (
      <EmptyState
        title="No funnel data"
        description="Funnel data will appear once analytics start flowing in."
      />
    );
  }
  const funnel = attributionFunnel(summary);
  return (
    <section className="mt-6 rounded-[28px] border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Revenue funnel</h2>
          <p className="mt-1 text-sm text-gray-500">
            Traffic, conversion, and customer value for this workspace.
          </p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <FunnelMetric label="Visit to lead" value={funnel.visitor_to_lead} />
        <FunnelMetric label="Lead to customer" value={funnel.lead_to_customer} />
        <FunnelMetric
          label="Revenue per customer"
          value={formatRevenue(funnel.revenue_per_customer_cents, summary.currency)}
        />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        <FunnelMetric label="Visits" value={String(summary.visits ?? 0)} />
        <FunnelMetric label="Leads" value={String(summary.leads ?? 0)} />
        <FunnelMetric label="Customers" value={String(summary.customers ?? 0)} />
        <FunnelMetric
          label="Revenue"
          value={formatRevenue(summary.revenue_cents ?? 0, summary.currency)}
        />
      </div>
    </section>
  );
}

function FunnelMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-md)] border border-gray-100 bg-gray-50 px-4 py-3">
      <p className="text-xs font-bold uppercase tracking-wide text-gray-400">{label}</p>
      <div className="mt-2 flex items-end justify-between gap-3">
        <p className="text-2xl font-black tabular-nums text-gray-950">{value}</p>
      </div>
    </div>
  );
}
