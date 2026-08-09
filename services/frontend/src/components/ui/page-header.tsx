import { type ComponentType, type ReactNode } from "react";

type IconType = ComponentType<{ className?: string }>;

/**
 * The single page header used by every logged-in ("/app") page: a consistent
 * brand-gradient icon tile, one title size (text-3xl), an optional subtitle and
 * eyebrow, and an optional actions slot on the right. Pages must not roll their
 * own title markup — route them through here so the treatment can never drift.
 */
export function PageHeader({
  icon: Icon,
  title,
  subtitle,
  eyebrow,
  actions,
}: {
  icon: IconType;
  title: string;
  subtitle?: string;
  eyebrow?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-4">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-og-green-950 via-og-green-700 to-og-green-600 text-white shadow-lg">
          <Icon className="h-6 w-6" />
        </span>
        <div>
          {eyebrow ? (
            <p className="text-xs font-bold uppercase tracking-wide text-gray-400">{eyebrow}</p>
          ) : null}
          <h1 className="text-3xl font-black tracking-tight text-gray-950">{title}</h1>
          {subtitle ? (
            <p className="mt-1 text-sm font-medium text-gray-500">{subtitle}</p>
          ) : null}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}
