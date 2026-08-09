"use client";

import { AppShell } from "@/components/ui/app-shell";
import { ButtonLink } from "@/components/ui/button";
import { StatusBadge, EmptyState } from "@/components/ui/data-display";
import { Skeleton, Stagger, StaggerItem, MotionLink } from "@/components/motion";
import { PageHeader } from "@/components/ui/page-header";
import { CalendarIcon, EmptyCalendar } from "@/components/illustrations";
import { useAuthGuard, useMe } from "@/features/auth";
import { appPath, appRootPath } from "@/lib/app-routes.mjs";
import { firstPaintLoading } from "@/lib/first-paint.mjs";
import { useMounted } from "@/lib/use-mounted";
import { calendarBucket, sortByDueDate } from "../calendar.mjs";
import { useContentList } from "../hooks";

const buckets: { name: string; dot: string }[] = [
  { name: "Overdue", dot: "bg-red-500" },
  { name: "Today", dot: "bg-og-green-600" },
  { name: "Tomorrow", dot: "bg-sky-500" },
  { name: "Later", dot: "bg-gray-400" },
];

export function ContentCalendar({ slug }: { slug?: string }) {
  const hasToken = useAuthGuard();
  const mounted = useMounted();
  const { data: me } = useMe(hasToken);
  const { data: items, isLoading, error } = useContentList();
  const tenantSlug = me?.tenant_slug ?? slug;
  const showLoading = firstPaintLoading(mounted, isLoading);
  const sorted = sortByDueDate(mounted ? items ?? [] : []);
  const isEmpty = !showLoading && sorted.length === 0;

  return (
    <AppShell>
      <section>
        <PageHeader
          icon={CalendarIcon}
          eyebrow="Content schedule"
          title="Calendar"
          actions={
            <ButtonLink href={appRootPath(tenantSlug)} variant="secondary">
              Dashboard
            </ButtonLink>
          }
        />

        {error && (
          <p className="mt-6 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
            {error instanceof Error ? error.message : "Failed to load calendar"}
          </p>
        )}

        {showLoading && (
          <div className="mt-6 grid gap-4 lg:grid-cols-4">
            {buckets.map((b) => (
              <Skeleton key={b.name} className="h-60 w-full" rounded="rounded-[var(--radius-lg)]" />
            ))}
          </div>
        )}

        {isEmpty && (
          <EmptyState
            className="mt-6"
            icon={<EmptyCalendar className="h-28 w-32" />}
            title="Nothing scheduled"
            description="Set a due date on any content piece and it'll show up here."
          />
        )}

        {!showLoading && !isEmpty && (
          <div className="mt-6 grid gap-4 lg:grid-cols-4">
            {buckets.map((bucket) => {
              const bucketItems = sorted.filter((item) => calendarBucket(item) === bucket.name);
              return (
                <section
                  key={bucket.name}
                  className="min-h-60 rounded-[var(--radius-lg)] border border-gray-200 bg-white p-4 shadow-card"
                >
                  <div className="flex items-center justify-between">
                    <h2 className="flex items-center gap-2 text-sm font-black text-gray-900">
                      <span className={`h-2 w-2 rounded-full ${bucket.dot}`} />
                      {bucket.name}
                    </h2>
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-bold text-gray-500">
                      {bucketItems.length}
                    </span>
                  </div>
                  <Stagger className="mt-4 space-y-3" amount={0.05}>
                    {bucketItems.map((item) => (
                      <StaggerItem key={item.id}>
                        <MotionLink
                          href={appPath(tenantSlug, "content", item.id)}
                          whileHover={{ y: -3 }}
                          transition={{ type: "spring", stiffness: 300, damping: 24 }}
                          className="block rounded-[var(--radius-md)] border border-gray-100 bg-gray-50 p-4 transition-colors hover:bg-white hover:shadow-card"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="min-w-0 truncate text-sm font-bold text-gray-900">
                              {item.title}
                            </h3>
                            <StatusBadge status={item.status} />
                          </div>
                          <p className="mt-3 text-xs font-medium text-gray-500">
                            {item.next_action ?? "No next action set"}
                          </p>
                          <p className="mt-2 text-xs font-bold text-gray-400">
                            {item.due_at
                              ? new Date(item.due_at).toLocaleDateString()
                              : "Unscheduled"}
                          </p>
                        </MotionLink>
                      </StaggerItem>
                    ))}
                    {bucketItems.length === 0 && (
                      <p className="rounded-[var(--radius-md)] border border-dashed border-gray-200 py-6 text-center text-xs font-medium text-gray-400">
                        No items
                      </p>
                    )}
                  </Stagger>
                </section>
              );
            })}
          </div>
        )}
      </section>
    </AppShell>
  );
}
