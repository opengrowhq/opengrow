"use client";

import Link from "next/link";
import type { AttributionTrend } from "../api";
import { compactTrendChartRows } from "../trend-chart.mjs";
import { TrendBar } from "./trend-chart";

export type BreakdownTrendItem = {
  key: string;
  label: string;
  href?: string;
  trend: Pick<AttributionTrend, "current" | "previous">;
};

/**
 * Up to three compact current-vs-previous cards above a breakdown table —
 * the per-breakdown counterpart of the executive TrendChart.
 */
export function BreakdownTrendCards({ items }: { items: BreakdownTrendItem[] }) {
  const top = items.slice(0, 3);
  if (top.length === 0) return null;
  return (
    <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {top.map((item) => (
        <div
          key={item.key}
          className="rounded-[var(--radius-md)] border border-gray-100 bg-gray-50 p-3"
        >
          <p className="mb-3 truncate text-xs font-bold text-gray-700" title={item.label}>
            {item.href ? (
              <Link href={item.href} className="hover:text-gray-950 hover:underline">
                {item.label}
              </Link>
            ) : (
              item.label
            )}
          </p>
          <div className="space-y-2.5">
            {compactTrendChartRows(item.trend).map((row) => (
              <div
                key={row.metric}
                className="grid grid-cols-[64px_minmax(0,1fr)] items-center gap-2"
              >
                <span className="text-[10px] font-semibold uppercase text-gray-400">
                  {row.label}
                </span>
                <div className="space-y-1">
                  <TrendBar value={row.current} width={row.currentWidth} tone="current" />
                  <TrendBar value={row.previous} width={row.previousWidth} tone="previous" />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
