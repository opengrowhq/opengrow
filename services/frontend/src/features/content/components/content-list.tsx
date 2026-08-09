"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/ui/app-shell";
import { Button, ButtonLink } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { StatusBadge, EmptyState, SegmentedControl } from "@/components/ui/data-display";
import { Skeleton, Stagger, StaggerItem, MotionLink } from "@/components/motion";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyDocs, LibraryIcon } from "@/components/illustrations";
import { useAuthGuard, useMe } from "@/features/auth";
import { appPath, appRootPath } from "@/lib/app-routes.mjs";
import { listViewState } from "@/lib/first-paint.mjs";
import { useMounted } from "@/lib/use-mounted";
import { useContentList, useCreateContent } from "../hooks";
import { contentOriginLabel } from "../lineage.mjs";

const FILTERS = [
  { key: "ALL", label: "All" },
  { key: "DRAFT", label: "Draft" },
  { key: "IN_REVIEW", label: "In review" },
  { key: "APPROVED", label: "Approved" },
  { key: "PUBLISHED", label: "Published" },
];

export function ContentList({ slug }: { slug?: string }) {
  const hasToken = useAuthGuard();
  const mounted = useMounted();
  const router = useRouter();
  const { data: me } = useMe(hasToken);
  const { data: items, isLoading, error } = useContentList();
  const create = useCreateContent();
  const [title, setTitle] = useState("");
  const [filter, setFilter] = useState("ALL");
  const tenantSlug = me?.tenant_slug ?? slug;
  const appHome = appRootPath(tenantSlug);
  const view = listViewState({ mounted, isLoading, count: items?.length ?? 0 });

  const filtered = useMemo(
    () => (filter === "ALL" ? items ?? [] : (items ?? []).filter((c) => c.status === filter)),
    [items, filter],
  );

  function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    create.mutate(
      { title: title.trim() },
      { onSuccess: (cp) => router.push(appPath(tenantSlug, "content", cp.id)) },
    );
  }

  return (
    <AppShell>
      <main className="space-y-6">
        <PageHeader
          icon={LibraryIcon}
          title="Library"
          subtitle="Everything you've created, in one place."
          actions={
            <ButtonLink href={appHome} variant="secondary">
              Studio
            </ButtonLink>
          }
        />

        {error && (
          <p className="rounded-xl bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-700">
            {error instanceof Error ? error.message : "Failed to load content"}
          </p>
        )}

        <form
          onSubmit={onCreate}
          className="flex gap-2 rounded-[var(--radius-lg)] border border-gray-200 bg-white p-3 shadow-card"
        >
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="New content title…"
            className="flex-1 border-0 bg-gray-50 focus:bg-gray-100 focus:ring-0"
          />
          <Button type="submit" loading={create.isPending}>
            Create
          </Button>
        </form>

        {view === "list" && (
          <SegmentedControl options={FILTERS} value={filter} onChange={setFilter} />
        )}

        {view === "loading" && (
          <div className="space-y-3">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full" rounded="rounded-[var(--radius-lg)]" />
            ))}
          </div>
        )}

        {view === "empty" && (
          <EmptyState
            icon={<EmptyDocs className="h-28 w-32" />}
            title="No content yet"
            description="Create your first piece, or head to the studio to generate one from your brand."
            action={
              <ButtonLink href={appHome} variant="primary">
                Open studio
              </ButtonLink>
            }
          />
        )}

        {view === "list" &&
          (filtered.length === 0 ? (
            <EmptyState title="Nothing here" description="No content matches this filter." />
          ) : (
            <Stagger className="space-y-3">
              {filtered.map((cp) => (
                <StaggerItem key={cp.id}>
                  <MotionLink
                    href={appPath(tenantSlug, "content", cp.id)}
                    whileHover={{ y: -3 }}
                    transition={{ type: "spring", stiffness: 300, damping: 24 }}
                    className="flex items-center justify-between gap-4 rounded-[var(--radius-lg)] border border-gray-200 bg-white px-5 py-4 shadow-card transition-shadow hover:shadow-lift"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-bold text-gray-900">
                        {cp.title}
                      </span>
                      {cp.next_action && (
                        <span className="mt-0.5 block truncate text-xs font-medium text-gray-400">
                          Next: {cp.next_action}
                        </span>
                      )}
                      {contentOriginLabel(cp) && (
                        <span className="mt-0.5 block truncate text-xs font-semibold text-emerald-700">
                          {contentOriginLabel(cp)}
                        </span>
                      )}
                    </span>
                    <StatusBadge status={cp.status} />
                  </MotionLink>
                </StaggerItem>
              ))}
            </Stagger>
          ))}
      </main>
    </AppShell>
  );
}
