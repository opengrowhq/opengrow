"use client";
import { EmptyState } from "@/components/ui/data-display";
import type { AttributionSummary } from "../api";
import { topAttributionRows } from "../rank.mjs";

export type BreakdownColumn<T> = {
  key: string;
  label: string;
  render: (row: T) => React.ReactNode;
};

export function BreakdownTable<T extends AttributionSummary>({
  rows,
  label,
  columns,
  limit,
}: {
  rows?: T[];
  label: (row: T) => string;
  columns: BreakdownColumn<T>[];
  limit?: number;
}) {
  const ranked = topAttributionRows(rows ?? [], limit ?? 10);
  if (ranked.length === 0) {
    return (
      <EmptyState
        title="Nothing to show"
        description="Data will appear here once it starts flowing in."
      />
    );
  }
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2 px-3 text-[11px] font-semibold uppercase text-gray-400">
        {columns.map((col) => (
          <span key={col.key}>{col.label}</span>
        ))}
      </div>
      {ranked.map((row, index) => (
        <div
          key={`${label(row)}-${index}`}
          className="rounded-2xl border border-gray-100 bg-gray-50 p-3"
        >
          <p className="truncate text-sm font-semibold">{label(row)}</p>
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-gray-500">
            {columns.map((col) => (
              <span key={col.key}>{col.render(row)}</span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
