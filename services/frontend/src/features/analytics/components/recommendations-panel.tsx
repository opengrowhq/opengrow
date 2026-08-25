"use client";

import type { ContentRecommendation } from "../api";
import {
  useDismissRecommendation,
  useRecommendations,
  useStartRunFromRecommendation,
} from "../hooks";

const kindLabel: Record<ContentRecommendation["kind"], string> = {
  REFRESH: "Refresh",
  DOUBLE_DOWN: "Double down",
  NEW_TOPIC: "New topic",
};

const kindTone: Record<ContentRecommendation["kind"], string> = {
  REFRESH: "bg-amber-100 text-amber-700",
  DOUBLE_DOWN: "bg-emerald-100 text-emerald-700",
  NEW_TOPIC: "bg-sky-100 text-sky-700",
};

/**
 * Real, backend-computed recommendations (REFRESH/DOUBLE_DOWN from actual
 * traffic deltas, NEW_TOPIC from tag-coverage gaps) — the attribution
 * loop's "what to write next" feedback step. Distinct from NextMoves,
 * which is an older client-side-only rule panel kept for the funnel/
 * tracking-install nudges it still covers.
 */
export function RecommendationsPanel() {
  const { data: recommendations, isLoading, error } = useRecommendations();
  const dismiss = useDismissRecommendation();
  const startRun = useStartRunFromRecommendation();

  return (
    <section className="rounded-[28px] border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold">Recommendations</h2>

      {isLoading && (
        <p className="mt-4 rounded-2xl border border-dashed border-gray-200 py-5 text-center text-xs text-gray-400">
          Loading…
        </p>
      )}

      {error && (
        <p className="mt-4 rounded-2xl border border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700">
          Couldn&rsquo;t load recommendations.
        </p>
      )}

      {!isLoading && !error && (recommendations ?? []).length === 0 && (
        <p className="mt-4 rounded-2xl border border-dashed border-gray-200 py-5 text-center text-xs text-gray-400">
          No recommendations yet — check back after the next daily sweep.
        </p>
      )}

      <div className="mt-4 space-y-2">
        {(recommendations ?? []).map((rec) => (
          <div
            key={rec.id}
            className="rounded-2xl border border-gray-100 bg-gray-50 p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <span
                  className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${kindTone[rec.kind]}`}
                >
                  {kindLabel[rec.kind]}
                </span>
                <p className="mt-1.5 text-sm font-semibold text-gray-900">
                  {rec.title}
                </p>
                <p className="mt-0.5 text-xs text-gray-500">{rec.rationale}</p>
              </div>
              <div className="flex shrink-0 flex-col gap-2">
                <button
                  type="button"
                  onClick={() => startRun.mutate(rec.id)}
                  disabled={startRun.isPending}
                  className="rounded-full bg-gray-950 px-3 py-1.5 text-xs font-semibold text-white shadow-sm disabled:opacity-50"
                >
                  Start run
                </button>
                <button
                  type="button"
                  onClick={() => dismiss.mutate(rec.id)}
                  disabled={dismiss.isPending}
                  className="rounded-full border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-500 hover:bg-white disabled:opacity-50"
                >
                  Dismiss
                </button>
              </div>
            </div>
            {(startRun.isError || dismiss.isError) && (
              <p className="mt-2 rounded-2xl border border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700">
                {(startRun.error instanceof Error && startRun.error.message) ||
                  (dismiss.error instanceof Error && dismiss.error.message) ||
                  "Something went wrong."}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
