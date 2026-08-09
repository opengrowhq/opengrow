"use client";

import type {
  AttributionSummary,
  ChannelAttribution,
  ContentAttribution,
  TrackingStatus,
} from "../api";
import { attributionRecommendations } from "../recommendations.mjs";

const toneDot: Record<string, string> = {
  urgent: "bg-red-500",
  warning: "bg-amber-500",
  growth: "bg-emerald-500",
  neutral: "bg-gray-300",
};

/**
 * "Next moves" — up to three prioritised, rule-based actions derived from
 * data the dashboard already fetches (no backend round-trip).
 */
export function NextMoves({
  summary,
  topContent,
  topChannels,
  trackingStatus,
}: {
  summary?: AttributionSummary;
  topContent?: ContentAttribution[];
  topChannels?: ChannelAttribution[];
  trackingStatus?: TrackingStatus;
}) {
  const recommendations = attributionRecommendations({
    summary,
    topContent,
    topChannels,
    trackingStatus,
  });
  return (
    <section
      aria-label="Next moves"
      className="rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card"
    >
      <h2 className="mb-3 text-sm font-black text-gray-900">Next moves</h2>
      <ul className="space-y-3">
        {recommendations.map((rec) => (
          <li key={rec.title} className="flex items-start gap-3">
            <span
              aria-hidden
              className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${toneDot[rec.tone] ?? toneDot.neutral}`}
            />
            <div>
              <p className="text-sm font-semibold text-gray-900">{rec.title}</p>
              <p className="mt-0.5 text-xs font-medium text-gray-500">{rec.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
