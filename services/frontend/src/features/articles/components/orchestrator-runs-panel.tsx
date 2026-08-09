"use client";

import { useState } from "react";
import Link from "next/link";
import { Badge, statusTone } from "@/components/ui/data-display";
import { Button } from "@/components/ui/button";
import { appPath } from "@/lib/app-routes.mjs";
import { ArticleOutlineEditor, nextSectionId, type OutlineSection } from "./article-outline-editor";
import {
  useApproveOrchestratorOutline,
  useOrchestratorRun,
  useOrchestratorRuns,
  useResumeOrchestratorRun,
} from "../orchestrator-hooks";
import type { OrchestratorRun } from "../orchestrator-api";

const panelCls =
  "rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card";

export function OrchestratorRunsPanel({
  tenantSlug,
  selectedRunId,
  onSelectRun,
}: {
  tenantSlug?: string;
  selectedRunId: string | null;
  onSelectRun: (id: string | null) => void;
}) {
  const { data: runs, isLoading } = useOrchestratorRuns();

  return (
    <section aria-label="Orchestrator runs" className={panelCls}>
      <h2 className="mb-4 text-sm font-black text-gray-900">Orchestrator runs</h2>
      {isLoading ? (
        <p className="text-xs font-medium text-gray-400">Loading runs…</p>
      ) : (runs ?? []).length === 0 ? (
        <p className="text-xs font-medium text-gray-400">
          No runs yet — use “Run with orchestrator” on a brief to start one.
        </p>
      ) : (
        <ul className="space-y-2">
          {(runs ?? []).map((run) => (
            <li key={run.run_id}>
              <button
                type="button"
                onClick={() =>
                  onSelectRun(selectedRunId === run.run_id ? null : run.run_id)
                }
                aria-expanded={selectedRunId === run.run_id}
                className={`flex w-full items-center justify-between gap-3 rounded-[var(--radius-md)] border px-3 py-2 text-left transition-colors ${
                  selectedRunId === run.run_id
                    ? "border-gray-400 bg-gray-50"
                    : "border-gray-100 hover:border-gray-200 hover:bg-gray-50"
                }`}
              >
                <span className="min-w-0 truncate text-xs font-semibold text-gray-700">
                  {runTitle(run)}
                </span>
                <Badge tone={statusTone(run.status)}>{run.status.replaceAll("_", " ")}</Badge>
              </button>
              {selectedRunId === run.run_id && (
                <RunDetail runId={run.run_id} tenantSlug={tenantSlug} />
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function runTitle(run: OrchestratorRun): string {
  const brief = (run.brief ?? "").trim().split("\n")[0];
  return brief ? brief.slice(0, 60) : `Run ${run.run_id.slice(0, 8)}`;
}

function RunDetail({ runId, tenantSlug }: { runId: string; tenantSlug?: string }) {
  const { data: run } = useOrchestratorRun(runId);
  const resume = useResumeOrchestratorRun();
  if (!run) return <p className="mt-2 text-xs text-gray-400">Loading…</p>;

  return (
    <div className="mt-2 rounded-[var(--radius-md)] border border-gray-100 bg-gray-50 p-4">
      <p className="text-xs font-semibold text-gray-500">
        Step: <span className="text-gray-800">{run.step ?? "—"}</span>
      </p>

      {run.status === "FAILED" && (
        <div className="mt-3">
          <p className="rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
            {run.error_message ?? "Run failed"}
          </p>
          <Button
            variant="secondary"
            size="sm"
            className="mt-3"
            loading={resume.isPending}
            onClick={() => resume.mutate(run.run_id)}
          >
            Resume run
          </Button>
        </div>
      )}

      {run.status === "AWAITING_OUTLINE_APPROVAL" && run.outline && (
        <OutlineApproval run={run} />
      )}

      {(run.status === "QUEUED" ||
        run.status === "GENERATING" ||
        run.status === "PROMOTING") && (
        <p className="mt-3 rounded-xl border border-sky-100 bg-sky-50 px-3 py-2 text-xs font-semibold text-sky-700" role="status">
          Working on it — this can take a few minutes on a local model.
        </p>
      )}

      {run.status === "COMPLETE" && run.content_piece_id && (
        <p className="mt-3 text-xs font-semibold">
          <Link
            href={appPath(tenantSlug, "content", run.content_piece_id)}
            className="text-interactive hover:underline"
          >
            Open the content piece →
          </Link>
        </p>
      )}
    </div>
  );
}

function OutlineApproval({ run }: { run: OrchestratorRun }) {
  const approve = useApproveOrchestratorOutline();
  const [sections, setSections] = useState<OutlineSection[]>(() =>
    (run.outline ?? []).map((s) => ({ ...s, id: nextSectionId() })),
  );

  return (
    <div className="mt-4">
      <p className="mb-3 text-xs font-semibold text-gray-500">
        Review the outline — edit anything, then approve to write the draft.
      </p>
      <ArticleOutlineEditor
        sections={sections}
        onChange={setSections}
        onWriteDraft={() =>
          approve.mutate({
            id: run.run_id,
            outline: sections
              .map((s) => ({ heading: s.heading.trim(), points: s.points.map((p) => p.trim()).filter(Boolean) }))
              .filter((s) => s.heading),
          })
        }
        writeLabel="Approve outline & write draft"
        pending={approve.isPending}
      />
      {approve.error instanceof Error && (
        <p className="mt-3 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
          {approve.error.message}
        </p>
      )}
    </div>
  );
}
