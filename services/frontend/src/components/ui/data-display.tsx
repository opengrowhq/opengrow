"use client";

import { type ReactNode } from "react";
import { motion } from "motion/react";
import { Counter } from "@/components/motion";

/* ----------------------------------- Badge ---------------------------------- */

type Tone = "neutral" | "success" | "warning" | "danger" | "info" | "gradient";

const toneClass: Record<Tone, string> = {
  neutral: "bg-gray-100 text-gray-700",
  success: "bg-emerald-100 text-emerald-700",
  warning: "bg-amber-100 text-amber-700",
  danger: "bg-red-100 text-red-700",
  info: "bg-sky-100 text-sky-700",
  // a11y: white on the brand interactive green #15803D is 5.02:1.
  gradient: "bg-interactive text-white",
};

/** Maps a backend status string to a semantic tone (mirrors old status-pill). */
export function statusTone(status: string): Tone {
  const s = status.toUpperCase();
  if (s.includes("FAIL")) return "danger";
  if (["INDEXED", "COMPLETE", "PUBLISHED", "APPROVED", "PR_OPENED", "READY"].includes(s))
    return "success";
  return "warning";
}

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${toneClass[tone]} ${className ?? ""}`}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={statusTone(status)}>{status.replaceAll("_", " ")}</Badge>;
}

/* --------------------------------- StatCard --------------------------------- */

export function StatCard({
  label,
  value,
  delta,
  icon,
  animate = true,
}: {
  label: string;
  value: number | string;
  delta?: { value: string; positive?: boolean };
  icon?: ReactNode;
  animate?: boolean;
}) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wide text-gray-400">{label}</span>
        {icon && <span className="text-gray-400">{icon}</span>}
      </div>
      <div className="mt-3 text-3xl font-black tabular-nums text-gray-950">
        {typeof value === "number" && animate ? <Counter to={value} /> : value}
      </div>
      {delta && (
        <div
          // a11y: this is text-xs, so both branches need 4.5:1. emerald-600 is
          // 3.67:1 and gray-400 is 2.60:1 on white; emerald-700 (5.37:1) and
          // gray-500 (4.84:1) clear it.
          className={`mt-2 text-xs font-bold ${delta.positive ? "text-emerald-700" : "text-gray-500"}`}
        >
          {delta.value}
        </div>
      )}
    </div>
  );
}

/* -------------------------------- EmptyState -------------------------------- */

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-[var(--radius-lg)] border border-dashed border-gray-300 bg-gray-50/60 px-6 py-14 text-center ${className ?? ""}`}
    >
      {icon && <div className="mb-4">{icon}</div>}
      <h3 className="text-lg font-black text-gray-800">{title}</h3>
      {description && (
        <p className="mt-2 max-w-sm text-sm font-medium text-gray-500">{description}</p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

/* ---------------------------------- Tabs ------------------------------------ */

export function Tabs({
  tabs,
  active,
  onChange,
  className,
}: {
  tabs: { key: string; label: ReactNode }[];
  active: string;
  onChange: (key: string) => void;
  className?: string;
}) {
  return (
    <div className={`flex gap-1 border-b border-gray-200 ${className ?? ""}`}>
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={`relative px-4 py-2.5 text-sm font-bold transition-colors ${
            active === t.key ? "text-gray-950" : "text-gray-500 hover:text-gray-800"
          }`}
        >
          {t.label}
          {active === t.key && (
            <motion.span
              layoutId="tab-underline"
              className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-grad"
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
            />
          )}
        </button>
      ))}
    </div>
  );
}

/* ----------------------------- SegmentedControl ----------------------------- */

export function SegmentedControl({
  options,
  value,
  onChange,
  className,
}: {
  options: { key: string; label: ReactNode }[];
  value: string;
  onChange: (key: string) => void;
  className?: string;
}) {
  return (
    <div
      className={`inline-flex rounded-full border border-gray-200 bg-gray-100 p-1 ${className ?? ""}`}
    >
      {options.map((o) => (
        <button
          key={o.key}
          onClick={() => onChange(o.key)}
          className="relative rounded-full px-3.5 py-1.5 text-xs font-bold text-gray-600 transition-colors"
        >
          {value === o.key && (
            <motion.span
              layoutId="segmented-active"
              className="absolute inset-0 rounded-full bg-white shadow-sm"
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
            />
          )}
          <span className={`relative ${value === o.key ? "text-gray-950" : ""}`}>{o.label}</span>
        </button>
      ))}
    </div>
  );
}
