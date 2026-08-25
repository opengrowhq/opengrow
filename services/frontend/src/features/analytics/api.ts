import { API_BASE, apiGet, apiSend, authHeaders, parse } from "@/lib/http";
import { analyticsWindowQuery } from "./window.mjs";

export type AttributionSummary = {
  events: number;
  visits: number;
  signups: number;
  leads: number;
  customers: number;
  revenue_cents: number;
  currency: string;
};

export type ContentAttribution = AttributionSummary & {
  content_piece_id: string;
  title: string;
  status: string;
};

export type SourceAttribution = AttributionSummary & {
  source_url: string;
};

export type ChannelAttribution = AttributionSummary & {
  channel: string;
};

export type TrackingStatus = {
  installed: boolean;
  events: number;
  first_party_visits: number;
  first_party_conversions: number;
  last_seen_at: string | null;
};

export type AttributionDelta = {
  absolute: number;
  percent: number | null;
};

export type AttributionTrend = {
  days: number;
  current: AttributionSummary;
  previous: AttributionSummary;
  deltas: Record<string, AttributionDelta>;
};

export type ChannelTrend = Omit<AttributionTrend, "days"> & {
  channel: string;
};

export type SourceTrend = Omit<AttributionTrend, "days"> & {
  source_url: string;
};

export type ContentTrend = Omit<AttributionTrend, "days"> & {
  content_piece_id: string;
  title: string;
  status: string;
};

export type RevenueEventInput = {
  event_type: string;
  content_piece_id?: string;
  event_count?: number;
  amount_cents?: number;
  currency?: string;
  provider?: string;
  channel?: string;
  dedupe_key?: string;
  source_url?: string;
  occurred_at?: string;
  metadata?: Record<string, unknown>;
};

export type AnalyticsImportProvider = "ga4" | "gsc" | "manual";

export type AnalyticsImportRow = {
  content_piece_id?: string;
  source_url?: string;
  channel?: string;
  external_id?: string;
  visits?: number;
  signups?: number;
  leads?: number;
  customers?: number;
  revenue_cents?: number;
  currency?: string;
  occurred_at?: string;
  metadata?: Record<string, unknown>;
};

export type AnalyticsImportInput = {
  provider: AnalyticsImportProvider;
  rows: AnalyticsImportRow[];
};

export type AnalyticsImportResult = {
  imported_events: number;
  imported_rows: number;
};

export type AnalyticsConnector = {
  id: string;
  provider: "ga4" | "gsc";
  status: string;
  display_name: string;
  external_property_id: string | null;
  site_url: string | null;
  scopes: string[];
  last_sync_at: string | null;
  last_sync_error: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type AnalyticsConnectorInput = {
  provider: "ga4" | "gsc";
  display_name: string;
  external_property_id?: string;
  site_url?: string;
  metadata?: Record<string, unknown>;
};

export type GoogleAuthUrl = {
  configured: boolean;
  provider: "ga4" | "gsc";
  scopes: string[];
  auth_url: string | null;
  state: string | null;
  message: string | null;
};

export type AnalyticsConnectorSyncResult = {
  connector_id: string;
  task_id: string | null;
  status: string;
};

export type AnalyticsWindow = "7" | "30" | "90" | "all";

export type ContentRecommendation = {
  id: string;
  kind: "REFRESH" | "DOUBLE_DOWN" | "NEW_TOPIC";
  content_piece_id: string | null;
  title: string;
  rationale: string;
  score: number;
  status: "PENDING" | "ACTIONED" | "DISMISSED";
  orchestrator_run_id: string | null;
  created_at: string;
};

export const getAttributionSummary = (window: AnalyticsWindow = "all") =>
  apiGet<AttributionSummary>(`/analytics/summary${analyticsWindowQuery(window)}`);

export const getAttributionTrend = (window: AnalyticsWindow = "30") =>
  apiGet<AttributionTrend>(
    `/analytics/trends${analyticsWindowQuery(window) || "?days=30"}`,
  );

export const getContentAttribution = (window: AnalyticsWindow = "all") =>
  apiGet<ContentAttribution[]>(`/analytics/content${analyticsWindowQuery(window)}`);

export const getSourceAttribution = (window: AnalyticsWindow = "all") =>
  apiGet<SourceAttribution[]>(`/analytics/sources${analyticsWindowQuery(window)}`);

export const getChannelAttribution = (window: AnalyticsWindow = "all") =>
  apiGet<ChannelAttribution[]>(`/analytics/channels${analyticsWindowQuery(window)}`);

export const getChannelTrends = (window: AnalyticsWindow = "30") =>
  apiGet<ChannelTrend[]>(
    `/analytics/channel-trends${analyticsWindowQuery(window) || "?days=30"}`,
  );

export const getSourceTrends = (window: AnalyticsWindow = "30") =>
  apiGet<SourceTrend[]>(
    `/analytics/source-trends${analyticsWindowQuery(window) || "?days=30"}`,
  );

export const getContentTrends = (window: AnalyticsWindow = "30") =>
  apiGet<ContentTrend[]>(
    `/analytics/content-trends${analyticsWindowQuery(window) || "?days=30"}`,
  );

export const getTrackingStatus = (window: AnalyticsWindow = "all") =>
  apiGet<TrackingStatus>(
    `/analytics/tracking/status${analyticsWindowQuery(window)}`,
  );

export const createRevenueEvent = (body: RevenueEventInput) =>
  apiSend("/analytics/events", "POST", body);

export const importAnalyticsEvents = (body: AnalyticsImportInput) =>
  apiSend<AnalyticsImportResult>("/analytics/import", "POST", body);

export async function importAnalyticsEventsCsv(
  file: File,
  provider: AnalyticsImportProvider = "manual",
): Promise<AnalyticsImportResult> {
  const form = new FormData();
  form.append("file", file);
  return parse(
    await fetch(`${API_BASE}/analytics/import/csv?provider=${provider}`, {
      method: "POST",
      headers: authHeaders(), // no Content-Type — browser sets multipart boundary
      body: form,
    }),
  );
}

export const listAnalyticsConnectors = () =>
  apiGet<AnalyticsConnector[]>("/analytics/connectors");

export const createAnalyticsConnector = (body: AnalyticsConnectorInput) =>
  apiSend<AnalyticsConnector>("/analytics/connectors", "POST", body);

export const disconnectAnalyticsConnector = (id: string) =>
  apiSend<AnalyticsConnector>(`/analytics/connectors/${id}/disconnect`, "POST", {});

export const completeGoogleConnectorOAuth = (id: string, code: string, state: string) =>
  apiSend<AnalyticsConnector>(
    `/analytics/connectors/${id}/google/callback`,
    "POST",
    { code, state },
  );

export const syncAnalyticsConnector = (id: string) =>
  apiSend<AnalyticsConnectorSyncResult>(`/analytics/connectors/${id}/sync`, "POST", {});

export const getGoogleAuthUrl = (provider: "ga4" | "gsc") =>
  apiGet<GoogleAuthUrl>(`/analytics/connectors/google/auth-url?provider=${provider}`);

export const listRecommendations = (status: string = "PENDING") =>
  apiGet<ContentRecommendation[]>(`/analytics/recommendations?status=${status}`);

export const dismissRecommendation = (id: string) =>
  apiSend<ContentRecommendation>(`/analytics/recommendations/${id}/dismiss`, "POST", {});

export const startRunFromRecommendation = (id: string) =>
  apiSend<ContentRecommendation>(
    `/analytics/recommendations/${id}/start-run`,
    "POST",
    {},
  );
