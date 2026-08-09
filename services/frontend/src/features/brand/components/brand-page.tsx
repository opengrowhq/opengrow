"use client";

import { useState } from "react";
import { AppShell } from "@/components/ui/app-shell";
import { ButtonLink } from "@/components/ui/button";
import { StatusBadge, EmptyState } from "@/components/ui/data-display";
import { Skeleton, Stagger, StaggerItem, motion } from "@/components/motion";
import { PageHeader } from "@/components/ui/page-header";
import { BrandIcon, BrandMark } from "@/components/illustrations";
import { useAuthGuard, useMe } from "@/features/auth";
import { appPath } from "@/lib/app-routes.mjs";
import { listViewState } from "@/lib/first-paint.mjs";
import { useMounted } from "@/lib/use-mounted";
import { useBrand, useBrands } from "../hooks";
import { BrandProfileEditor } from "./brand-profile-editor";

export function BrandPage({ slug }: { slug?: string }) {
  const hasToken = useAuthGuard();
  const mounted = useMounted();
  const { data: me } = useMe(hasToken);
  const { data: brands, isLoading } = useBrands();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data: selected } = useBrand(selectedId);
  const tenantSlug = me?.tenant_slug ?? slug;
  const view = listViewState({ mounted, isLoading, count: brands?.length ?? 0 });

  return (
    <AppShell>
      <main className="space-y-6">
        <PageHeader
          icon={BrandIcon}
          title="Brand DNA"
          subtitle="Teach OpenGrow how your brand sounds, looks, and sells."
          actions={
            <ButtonLink href={appPath(tenantSlug, "onboarding")} variant="primary">
              + New brand
            </ButtonLink>
          }
        />

        {view === "loading" && (
          <div className="space-y-3">
            {[0, 1].map((i) => (
              <Skeleton key={i} className="h-16 w-full" rounded="rounded-[var(--radius-lg)]" />
            ))}
          </div>
        )}

        {view === "empty" && (
          <EmptyState
            icon={<BrandMark className="h-16 w-16" />}
            title="No brands yet"
            description="Add a brand and OpenGrow will learn its voice from your website automatically."
            action={
              <ButtonLink href={appPath(tenantSlug, "onboarding")}>Set one up</ButtonLink>
            }
          />
        )}

        {view === "list" && (
          <Stagger className="space-y-3">
            {brands?.map((b) => (
              <StaggerItem key={b.id}>
                <motion.button
                  onClick={() => setSelectedId(b.id)}
                  whileHover={{ y: -3 }}
                  transition={{ type: "spring", stiffness: 300, damping: 24 }}
                  className={`flex w-full items-center justify-between gap-4 rounded-[var(--radius-lg)] border bg-white px-5 py-4 text-left shadow-card transition-shadow hover:shadow-lift ${
                    selectedId === b.id ? "border-interactive ring-1 ring-og-green-200" : "border-gray-200"
                  }`}
                >
                  <span className="flex min-w-0 items-center gap-3">
                    <BrandMark className="h-9 w-9 shrink-0" />
                    <span className="truncate text-sm font-bold text-gray-900">{b.name}</span>
                  </span>
                  <StatusBadge status={b.status} />
                </motion.button>
              </StaggerItem>
            ))}
          </Stagger>
        )}

        {selected && (
          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="space-y-4 rounded-[var(--radius-lg)] border border-gray-200 bg-white p-6 shadow-card"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-black">{selected.name}</h2>
              <StatusBadge status={selected.status} />
            </div>
            {selected.source_url && (
              <p className="truncate text-sm font-medium text-gray-500">{selected.source_url}</p>
            )}
            {selected.status !== "READY" && selected.status !== "FAILED" ? (
              <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-700">
                Learning your brand… this refreshes automatically.
              </p>
            ) : (
              <BrandProfileEditor brand={selected} />
            )}
          </motion.section>
        )}
      </main>
    </AppShell>
  );
}
