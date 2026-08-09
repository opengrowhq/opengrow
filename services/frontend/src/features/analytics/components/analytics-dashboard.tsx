"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/ui/app-shell";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState, SegmentedControl, Tabs } from "@/components/ui/data-display";
import { ChartIcon } from "@/components/illustrations";
import { useAuthGuard, useMe } from "@/features/auth";
import { appPath } from "@/lib/app-routes.mjs";
import type { AnalyticsWindow } from "../api";
import { analyticsWindows, analyticsWindowLabel } from "../window.mjs";
import {
  useAttributionSummary,
  useAttributionTrend,
  useContentAttribution,
  useChannelAttribution,
  useSourceAttribution,
  useChannelTrends,
  useContentTrends,
  useSourceTrends,
  useTrackingStatus,
} from "../hooks";
import { KpiSummary } from "./kpi-summary";
import { RevenueFunnel } from "./revenue-funnel";
import { TrendChart } from "./trend-chart";
import { NextMoves } from "./next-moves";
import { BreakdownTable } from "./breakdown-table";
import { BreakdownTrendCards } from "./breakdown-trend-cards";
import { TrackingStatusCard } from "./tracking-status-card";
import { ConnectorsPanel } from "./connectors-panel";
import { ImportRevenuePanel } from "./import-revenue-panel";

export function AnalyticsDashboard() {
  const hasToken = useAuthGuard();
  const params = useParams<{ slug: string }>();
  const { data: me } = useMe(hasToken);
  const [win, setWin] = useState<AnalyticsWindow>("30");
  const [tab, setTab] = useState("content");

  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
  } = useAttributionSummary(win);
  const { data: trend } = useAttributionTrend(win);
  const {
    data: content,
    isLoading: contentLoading,
    error: contentError,
  } = useContentAttribution(win);
  const {
    data: channels,
    isLoading: channelsLoading,
    error: channelsError,
  } = useChannelAttribution(win);
  const {
    data: sources,
    isLoading: sourcesLoading,
    error: sourcesError,
  } = useSourceAttribution(win);
  const { data: tracking } = useTrackingStatus(win);
  const { data: contentTrends } = useContentTrends(win);
  const { data: channelTrends } = useChannelTrends(win);
  const { data: sourceTrends } = useSourceTrends(win);

  const breakdownState: Record<string, { isLoading: boolean; error: unknown }> = {
    content: { isLoading: contentLoading, error: contentError },
    channels: { isLoading: channelsLoading, error: channelsError },
    sources: { isLoading: sourcesLoading, error: sourcesError },
  };
  const activeBreakdown = breakdownState[tab];

  const currency = summary?.currency ?? "USD";
  const slug = me?.tenant_slug ?? params.slug;

  return (
    <AppShell>
      <PageHeader
        icon={ChartIcon}
        title="Analytics"
        actions={
          <SegmentedControl
            options={analyticsWindows.map((w) => ({ key: w, label: analyticsWindowLabel(w) }))}
            value={win}
            onChange={(k) => setWin(k as AnalyticsWindow)}
          />
        }
      />

      {summaryLoading ? (
        <div className="mt-6">
          <SectionLoading />
        </div>
      ) : summaryError ? (
        <div className="mt-6">
          <SectionError error={summaryError} />
        </div>
      ) : (
        <>
          <div className="mt-6">
            <KpiSummary summary={summary} trend={trend} />
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <RevenueFunnel summary={summary} />
            <TrendChart trend={trend} currency={currency} />
          </div>

          <div className="mt-6">
            <NextMoves
              summary={summary}
              topContent={content}
              topChannels={channels}
              trackingStatus={tracking}
            />
          </div>
        </>
      )}

      <div className="mt-8">
        <Tabs
          tabs={[
            { key: "content", label: "Content" },
            { key: "channels", label: "Channels" },
            { key: "sources", label: "Sources" },
          ]}
          active={tab}
          onChange={setTab}
        />
        <div className="mt-4">
          {activeBreakdown.isLoading ? (
            <SectionLoading />
          ) : activeBreakdown.error ? (
            <SectionError error={activeBreakdown.error} />
          ) : (
            <>
              {tab === "content" && (
                <>
                  <BreakdownTrendCards
                    items={(contentTrends ?? []).map((t) => ({
                      key: t.content_piece_id,
                      label: t.title,
                      href: appPath(slug, "content", t.content_piece_id),
                      trend: t,
                    }))}
                  />
                  <BreakdownTable
                    rows={content}
                    label={(r) => r.title}
                    columns={[
                      { key: "visits", label: "Visits", render: (r) => r.visits },
                      { key: "signups", label: "Signups", render: (r) => r.signups },
                      { key: "customers", label: "Customers", render: (r) => r.customers },
                    ]}
                  />
                </>
              )}
              {tab === "channels" && (
                <>
                  <BreakdownTrendCards
                    items={(channelTrends ?? []).map((t) => ({
                      key: t.channel,
                      label: t.channel,
                      trend: t,
                    }))}
                  />
                  <BreakdownTable
                    rows={channels}
                    label={(r) => r.channel}
                    columns={[
                      { key: "visits", label: "Visits", render: (r) => r.visits },
                      { key: "customers", label: "Customers", render: (r) => r.customers },
                    ]}
                  />
                </>
              )}
              {tab === "sources" && (
                <>
                  <BreakdownTrendCards
                    items={(sourceTrends ?? []).map((t) => ({
                      key: t.source_url,
                      label: t.source_url,
                      trend: t,
                    }))}
                  />
                  <BreakdownTable
                    rows={sources}
                    label={(r) => r.source_url}
                    columns={[
                      { key: "visits", label: "Visits", render: (r) => r.visits },
                      { key: "customers", label: "Customers", render: (r) => r.customers },
                    ]}
                  />
                </>
              )}
            </>
          )}
        </div>
      </div>

      <div className="mt-10 space-y-6">
        <TrackingStatusCard status={tracking} tenantSlug={slug} />
        <ConnectorsPanel />
        <ImportRevenuePanel />
      </div>
    </AppShell>
  );
}

function SectionLoading() {
  return <EmptyState title="Loading…" description="Fetching the latest analytics." />;
}

function SectionError({ error }: { error: unknown }) {
  const message =
    error instanceof Error ? error.message : "Something went wrong loading analytics.";
  return (
    <EmptyState
      className="border-solid border-red-200 bg-red-50/60"
      title="Couldn't load analytics"
      description={message}
    />
  );
}
