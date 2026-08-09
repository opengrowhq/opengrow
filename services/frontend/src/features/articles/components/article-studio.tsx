"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/ui/app-shell";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Tabs } from "@/components/ui/data-display";
import { ArticleIcon } from "@/components/illustrations";
import { useAuthGuard, useMe } from "@/features/auth";
import { useBrands } from "@/features/brand";
import { useCreateFromGeneration } from "@/features/content";
import { appPath } from "@/lib/app-routes.mjs";
import { cleanArticleBrief, defaultArticleBrief, validateArticleBrief } from "../article-brief.mjs";
import { parseOutline } from "../outline.mjs";
import { slugify } from "../slugify.mjs";
import { useArticleGeneration, useCreateArticleGeneration } from "../hooks";
import { useCreateOrchestratorRun } from "../orchestrator-hooks";
import {
  ArticleBriefForm,
  type ArticleBriefErrors,
  type ArticleBriefValues,
} from "./article-brief-form";
import { ArticleOutlineEditor, nextSectionId, type OutlineSection } from "./article-outline-editor";
import { ArticleDraftPreview } from "./article-draft-preview";
import { OrchestratorRunsPanel } from "./orchestrator-runs-panel";

type Phase = "brief" | "outline" | "draft";

const panelCls =
  "mt-6 rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card";
const errorCls =
  "mt-4 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700";
const progressCls =
  "rounded-xl border border-sky-100 bg-sky-50 px-3 py-2 text-xs font-semibold text-sky-700";

export function ArticleStudio() {
  const hasToken = useAuthGuard();
  const router = useRouter();
  const { data: me } = useMe(hasToken);
  const { data: brands } = useBrands();

  const createGen = useCreateArticleGeneration();
  const saveContent = useCreateFromGeneration();
  const createRun = useCreateOrchestratorRun();

  const [brief, setBrief] = useState<ArticleBriefValues>(() => defaultArticleBrief());
  const [errors, setErrors] = useState<ArticleBriefErrors>({});
  // While the user hasn't typed a slug by hand, derive it live from the topic.
  const [slugTouched, setSlugTouched] = useState(false);
  const [phase, setPhase] = useState<Phase>("brief");
  const [backToBrief, setBackToBrief] = useState(false);
  const [outlineGenId, setOutlineGenId] = useState<string | null>(null);
  const [draftGenId, setDraftGenId] = useState<string | null>(null);
  const [sections, setSections] = useState<OutlineSection[]>([]);
  const [reviewOutline, setReviewOutline] = useState(true);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const outlineGen = useArticleGeneration(outlineGenId).data;
  const draftGen = useArticleGeneration(draftGenId).data;

  const outlineDone = outlineGen?.status === "COMPLETE";
  const outlineFailed = outlineGen?.status === "FAILED";
  const outlineInFlight = !!outlineGenId && !outlineDone && !outlineFailed;
  const draftDone = draftGen?.status === "COMPLETE";
  const draftFailed = draftGen?.status === "FAILED";

  // Parse the outline once per result so polling/re-renders never clobber edits.
  const parsedResultRef = useRef<string | null>(null);
  useEffect(() => {
    const result = outlineGen?.status === "COMPLETE" ? outlineGen.result : null;
    if (result && parsedResultRef.current !== result) {
      parsedResultRef.current = result;
      setSections(parseOutline(result).map((s) => ({ ...s, id: nextSectionId() })));
    }
  }, [outlineGen]);

  // Synchronous re-entrancy guard: a second Plan/Regenerate/Write-draft click
  // landing before the mutation state flips must not spawn a duplicate
  // (billable) generation.
  const startingRef = useRef(false);

  // Pre-fill tone/audience from the first READY brand while those fields are empty.
  // Adjusts state during render (the React-endorsed derived-state pattern) so it
  // stays in sync with the async brands query without an effect.
  const readyBrand = brands?.find((b) => b.status === "READY");
  const [prefilledBrandId, setPrefilledBrandId] = useState<string | null>(null);
  if (readyBrand?.profile && prefilledBrandId !== readyBrand.id) {
    setPrefilledBrandId(readyBrand.id);
    const tone = String(readyBrand.profile.tone ?? "");
    const audience = String(readyBrand.profile.audience ?? "");
    setBrief((b) => ({ ...b, tone: b.tone || tone, audience: b.audience || audience }));
  }

  const tenantSlug = me?.tenant_slug;
  const generatingOutline = phase === "outline" && !outlineDone && !outlineFailed;
  const generatingDraft = phase === "draft" && !draftDone && !draftFailed;
  const view: Phase =
    phase === "draft"
      ? "draft"
      : backToBrief
        ? "brief"
        : outlineDone || phase === "outline"
          ? "outline"
          : "brief";

  const errorMessage =
    outlineGen?.error_message ??
    draftGen?.error_message ??
    (createGen.error instanceof Error ? createGen.error.message : null) ??
    (saveContent.error instanceof Error ? saveContent.error.message : null);

  function startOutlineGeneration() {
    if (startingRef.current) return;
    startingRef.current = true;
    // A new outline invalidates everything derived from the previous one:
    // drop the parsed sections and any draft so no stale content shows
    // while the replacement is being generated. Snapshot them first so a
    // failed start can restore the user's edits instead of destroying them.
    const prevOutlineGenId = outlineGenId;
    const prevSections = sections;
    const prevDraftGenId = draftGenId;
    const prevParsedResult = parsedResultRef.current;
    parsedResultRef.current = null;
    setOutlineGenId(null);
    setSections([]);
    setDraftGenId(null);
    createGen.mutate(
      {
        brief: brief.topic.trim(),
        metadata: { kind: "article_outline", article: cleanArticleBrief(brief) },
      },
      {
        onSuccess: (g) => setOutlineGenId(g.id),
        onError: () => {
          // Restore the parse sentinel too, otherwise the effect re-parses
          // the old result and clobbers the just-restored edits.
          parsedResultRef.current = prevParsedResult;
          setOutlineGenId(prevOutlineGenId);
          setSections(prevSections);
          setDraftGenId(prevDraftGenId);
        },
        onSettled: () => {
          startingRef.current = false;
        },
      },
    );
  }

  function onPlan() {
    const fieldErrors = validateArticleBrief(brief) as ArticleBriefErrors;
    setErrors(fieldErrors);
    if (Object.keys(fieldErrors).length > 0) return;
    setBackToBrief(false);
    setPhase("outline");
    startOutlineGeneration();
  }

  function onRunOrchestrator() {
    const fieldErrors = validateArticleBrief(brief) as ArticleBriefErrors;
    setErrors(fieldErrors);
    if (Object.keys(fieldErrors).length > 0) return;
    createRun.mutate(
      {
        brief: brief.topic.trim(),
        article: cleanArticleBrief(brief),
        pause_for_outline_approval: reviewOutline,
      },
      { onSuccess: (run) => setSelectedRunId(run.run_id) },
    );
  }

  function onWriteDraft() {
    if (startingRef.current || sections.length === 0) return;
    startingRef.current = true;
    const outline = sections.map((s) => ({
      heading: s.heading.trim(),
      points: s.points.map((p) => p.trim()).filter(Boolean),
    }));
    createGen.mutate(
      {
        brief: brief.topic.trim(),
        parent_generation_id: outlineGenId,
        metadata: {
          kind: "article_draft",
          article: cleanArticleBrief(brief),
          outline,
        },
      },
      {
        // Move to the draft tab only once the generation actually started —
        // on failure the user stays on the outline with the error visible.
        onSuccess: (g) => {
          setDraftGenId(g.id);
          setPhase("draft");
        },
        onSettled: () => {
          startingRef.current = false;
        },
      },
    );
  }

  function onSave() {
    if (!draftGenId) return;
    saveContent.mutate(
      { generationId: draftGenId, title: brief.topic.trim() },
      { onSuccess: (cp) => router.push(appPath(tenantSlug, "content", cp.id)) },
    );
  }

  return (
    <AppShell>
      <section>
        <PageHeader
          icon={ArticleIcon}
          title="Article Studio"
          subtitle="From a brief to a structured outline to a full draft — on brand, ready to publish."
        />

        <Tabs
          className="mt-6"
          tabs={[
            { key: "brief", label: "1 · Brief" },
            { key: "outline", label: "2 · Outline" },
            { key: "draft", label: "3 · Draft" },
          ]}
          active={view}
          onChange={(key) => {
            if (key === "brief") {
              setBackToBrief(true);
              setPhase("brief");
            } else if (
              key === "outline" &&
              (outlineDone || outlineInFlight || outlineFailed || sections.length > 0)
            ) {
              setBackToBrief(false);
              setPhase("outline");
            } else if (key === "draft" && draftDone) {
              setBackToBrief(false);
              setPhase("draft");
            }
          }}
        />

        {errorMessage && <p className={errorCls}>{errorMessage}</p>}

        {view === "brief" && (
          <div className={panelCls}>
            <ArticleBriefForm
              brief={brief}
              errors={errors}
              onChange={(patch) => {
                if ("slug" in patch) setSlugTouched(Boolean(String(patch.slug).trim()));
                setBrief((b) => {
                  const next = { ...b, ...patch };
                  if ("topic" in patch && !slugTouched) {
                    next.slug = next.topic.trim() ? slugify(next.topic) : "";
                  }
                  return next;
                });
                // Clear the validation error for each field the user edits.
                setErrors((errs) => {
                  const next = { ...errs };
                  for (const key of Object.keys(patch) as (keyof ArticleBriefErrors)[]) {
                    delete next[key];
                  }
                  return next;
                });
              }}
              onSubmit={onPlan}
              pending={createGen.isPending}
            />
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 pt-4">
              <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-gray-500">
                <input
                  type="checkbox"
                  checked={reviewOutline}
                  onChange={(e) => setReviewOutline(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300"
                />
                Review outline before drafting
              </label>
              <Button
                variant="secondary"
                onClick={onRunOrchestrator}
                loading={createRun.isPending}
                disabled={!brief.topic.trim()}
              >
                Run with orchestrator
              </Button>
            </div>
            {createRun.error instanceof Error && (
              <p className={errorCls}>{createRun.error.message}</p>
            )}
          </div>
        )}

        {view === "outline" && (
          <div className={panelCls}>
            <h2 className="mb-4 text-sm font-black text-gray-900">Outline</h2>
            <div className="space-y-4">
              {generatingOutline ? (
                <p className={progressCls} role="status">
                  Planning your outline — generation can take a few minutes on a local model.
                </p>
              ) : (
                <ArticleOutlineEditor
                  sections={sections}
                  onChange={setSections}
                  onRegenerate={startOutlineGeneration}
                  onWriteDraft={onWriteDraft}
                  pending={createGen.isPending}
                />
              )}
            </div>
          </div>
        )}

        {view === "draft" && (
          <div className={panelCls}>
            <h2 className="mb-4 text-sm font-black text-gray-900">Draft</h2>
            {draftDone ? (
              <ArticleDraftPreview
                markdown={draftGen?.result ?? ""}
                onSave={onSave}
                pending={saveContent.isPending}
              />
            ) : (
              generatingDraft && (
                <p className={progressCls} role="status">
                  Writing your draft — generation can take a few minutes on a local model.
                </p>
              )
            )}
          </div>
        )}

        <div className="mt-8">
          <OrchestratorRunsPanel
            tenantSlug={tenantSlug}
            selectedRunId={selectedRunId}
            onSelectRun={setSelectedRunId}
          />
        </div>
      </section>
    </AppShell>
  );
}
