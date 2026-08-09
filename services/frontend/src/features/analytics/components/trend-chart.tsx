"use client";
import { EmptyState } from "@/components/ui/data-display";
import type { AttributionTrend } from "../api";
import { formatRevenue } from "../format.mjs";
import { trendChartRows } from "../trend-chart.mjs";

export function TrendChart({
  trend,
  currency = "USD",
}: {
  trend?: AttributionTrend;
  currency?: string;
}) {
  if (!trend) {
    return <EmptyState title="No trend data" description="Trend data will appear once analytics start flowing in." />;
  }
  const rows = trendChartRows(trend);
  return (
    <div className="mt-5 rounded-2xl border border-gray-100 bg-gray-50 p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-gray-900">Trend chart</h3>
        <div className="flex gap-3 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-gray-950" />
            Current
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-gray-300" />
            Previous
          </span>
        </div>
      </div>
      <div className="space-y-4">
        {rows.map((row) => (
          <div key={row.metric} className="grid gap-2 sm:grid-cols-[90px_minmax(0,1fr)]">
            <p className="text-xs font-semibold uppercase text-gray-400">
              {row.label}
            </p>
            <div className="space-y-1.5">
              <TrendBar
                value={row.current}
                width={row.currentWidth}
                currency={row.metric === "revenue_cents" ? currency : undefined}
                tone="current"
              />
              <TrendBar
                value={row.previous}
                width={row.previousWidth}
                currency={row.metric === "revenue_cents" ? currency : undefined}
                tone="previous"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function TrendBar({
  value,
  width,
  currency,
  tone,
}: {
  value: number;
  width: number;
  currency?: string;
  tone: "current" | "previous";
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_74px] items-center gap-2">
      <div className="h-3 overflow-hidden rounded-full bg-white">
        <div
          className={`h-full rounded-full ${
            tone === "current" ? "bg-gray-950" : "bg-gray-300"
          }`}
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="text-right text-xs font-semibold text-gray-500">
        {currency ? formatRevenue(value, currency) : value}
      </span>
    </div>
  );
}
