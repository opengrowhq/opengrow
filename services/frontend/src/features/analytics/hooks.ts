"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { loadToken } from "@/lib/auth";
import {
  type AnalyticsWindow,
  createRevenueEvent,
  createAnalyticsConnector,
  completeGoogleConnectorOAuth,
  disconnectAnalyticsConnector,
  getAttributionSummary,
  getAttributionTrend,
  getChannelAttribution,
  getChannelTrends,
  getContentTrends,
  getContentAttribution,
  getGoogleAuthUrl,
  getSourceAttribution,
  getSourceTrends,
  getTrackingStatus,
  importAnalyticsEvents,
  listAnalyticsConnectors,
  syncAnalyticsConnector,
} from "./api";

const hasToken = () => !!loadToken();

export function useAttributionSummary(window: AnalyticsWindow = "all") {
  return useQuery({
    queryKey: ["analytics", "summary", window],
    queryFn: () => getAttributionSummary(window),
    enabled: hasToken(),
  });
}

export function useAttributionTrend(window: AnalyticsWindow = "30") {
  return useQuery({
    queryKey: ["analytics", "trends", window],
    queryFn: () => getAttributionTrend(window === "all" ? "30" : window),
    enabled: hasToken() && window !== "all",
  });
}

export function useContentAttribution(window: AnalyticsWindow = "all") {
  return useQuery({
    queryKey: ["analytics", "content", window],
    queryFn: () => getContentAttribution(window),
    enabled: hasToken(),
  });
}

export function useSourceAttribution(window: AnalyticsWindow = "all") {
  return useQuery({
    queryKey: ["analytics", "sources", window],
    queryFn: () => getSourceAttribution(window),
    enabled: hasToken(),
  });
}

export function useChannelAttribution(window: AnalyticsWindow = "all") {
  return useQuery({
    queryKey: ["analytics", "channels", window],
    queryFn: () => getChannelAttribution(window),
    enabled: hasToken(),
  });
}

export function useChannelTrends(window: AnalyticsWindow = "30") {
  return useQuery({
    queryKey: ["analytics", "channel-trends", window],
    queryFn: () => getChannelTrends(window === "all" ? "30" : window),
    enabled: hasToken() && window !== "all",
  });
}

export function useSourceTrends(window: AnalyticsWindow = "30") {
  return useQuery({
    queryKey: ["analytics", "source-trends", window],
    queryFn: () => getSourceTrends(window === "all" ? "30" : window),
    enabled: hasToken() && window !== "all",
  });
}

export function useContentTrends(window: AnalyticsWindow = "30") {
  return useQuery({
    queryKey: ["analytics", "content-trends", window],
    queryFn: () => getContentTrends(window === "all" ? "30" : window),
    enabled: hasToken() && window !== "all",
  });
}

export function useTrackingStatus(window: AnalyticsWindow = "all") {
  return useQuery({
    queryKey: ["analytics", "tracking", "status", window],
    queryFn: () => getTrackingStatus(window),
    enabled: hasToken(),
  });
}

export function useCreateRevenueEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createRevenueEvent,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analytics"] }),
  });
}

export function useImportAnalyticsEvents() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: importAnalyticsEvents,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analytics"] }),
  });
}

export function useAnalyticsConnectors() {
  return useQuery({
    queryKey: ["analytics", "connectors"],
    queryFn: listAnalyticsConnectors,
    enabled: hasToken(),
  });
}

export function useCreateAnalyticsConnector() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createAnalyticsConnector,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analytics", "connectors"] }),
  });
}

export function useDisconnectAnalyticsConnector() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: disconnectAnalyticsConnector,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analytics", "connectors"] }),
  });
}

export function useGoogleAuthUrl() {
  return useMutation({
    mutationFn: getGoogleAuthUrl,
  });
}

export function useCompleteGoogleConnectorOAuth() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, code, state }: { id: string; code: string; state: string }) =>
      completeGoogleConnectorOAuth(id, code, state),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analytics", "connectors"] }),
  });
}

export function useSyncAnalyticsConnector() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: syncAnalyticsConnector,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analytics", "connectors"] }),
  });
}
