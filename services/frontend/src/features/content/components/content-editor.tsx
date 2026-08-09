"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { AppShell } from "@/components/ui/app-shell";
import { Button, ButtonLink } from "@/components/ui/button";
import { Field, controlClass } from "@/components/ui/field";
import { StatusBadge } from "@/components/ui/data-display";
import { useAuthGuard, useMe } from "@/features/auth";
import { appPath } from "@/lib/app-routes.mjs";
import { exportMarkdown } from "../api";
import {
  useContent,
  useGeneration,
  useTransitionContent,
  useUpdateContent,
} from "../hooks";
import { lineageRows, shortId } from "../lineage.mjs";
import { GitHubPublishPanel } from "./github-publish-panel";

const NEXT: Record<string, { to: string; label: string }[]> = {
  DRAFT: [{ to: "IN_REVIEW", label: "Review" }],
  IN_REVIEW: [
    { to: "APPROVED", label: "Approve" },
    { to: "DRAFT", label: "Draft" },
  ],
  APPROVED: [{ to: "DRAFT", label: "Draft" }],
  PUBLISHED: [{ to: "ARCHIVED", label: "Archive" }],
  ARCHIVED: [{ to: "DRAFT", label: "Restore" }],
};
const EDITABLE = new Set(["DRAFT", "IN_REVIEW"]);
const FLOW = ["DRAFT", "IN_REVIEW", "APPROVED", "PUBLISHED"];

const fieldCls = controlClass("py-2.5 disabled:opacity-60");

export function ContentEditor({ id, slug }: { id: string; slug?: string }) {
  const hasToken = useAuthGuard();
  const { data: me } = useMe(hasToken);
  const { data: cp, error } = useContent(id);
  const { data: draftGeneration } = useGeneration(cp?.source_generation_id);
  const { data: outlineGeneration } = useGeneration(draftGeneration?.parent_generation_id);
  const update = useUpdateContent(id);
  const transition = useTransitionContent(id);

  const titleRef = useRef<HTMLInputElement>(null);
  const bodyRef = useRef<HTMLTextAreaElement>(null);
  const nextActionRef = useRef<HTMLInputElement>(null);
  const dueAtRef = useRef<HTMLInputElement>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [localErr, setLocalErr] = useState<string | null>(null);

  if (!cp) {
    return (
      <AppShell>
        <div className="flex min-h-screen items-center justify-center text-sm font-medium text-gray-500">
          {error instanceof Error ? error.message : "Loading…"}
        </div>
      </AppShell>
    );
  }

  const editable = EDITABLE.has(cp.status);
  const activeStep = Math.max(FLOW.indexOf(cp.status), 0);

  function onSave() {
    setMsg(null);
    update.mutate(
      {
        title: editable ? titleRef.current?.value : undefined,
        body: editable ? bodyRef.current?.value : undefined,
        next_action: nextActionRef.current?.value ?? null,
        due_at: dueAtRef.current?.value ? new Date(dueAtRef.current.value).toISOString() : null,
      },
      { onSuccess: () => setMsg("Saved") },
    );
  }

  async function onExport() {
    setMsg(null);
    setLocalErr(null);
    try {
      const md = await exportMarkdown(id);
      const url = URL.createObjectURL(new Blob([md], { type: "text/markdown" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${id}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setLocalErr(e instanceof Error ? e.message : "Export failed");
    }
  }

  const anyErr =
    localErr ??
    (update.error instanceof Error ? update.error.message : null) ??
    (transition.error instanceof Error ? transition.error.message : null);
  const tenantSlug = me?.tenant_slug ?? slug;
  const lineage = lineageRows(cp, draftGeneration, outlineGeneration);

  return (
    <AppShell>
      <section>
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <ButtonLink href={appPath(tenantSlug, "content")} variant="secondary" size="sm">
            ← Library
          </ButtonLink>
          <StatusBadge status={cp.status} />
        </header>

        {/* Animated status stepper */}
        <div className="mb-6 grid gap-2 sm:grid-cols-4">
          {FLOW.map((step, index) => {
            const on = index <= activeStep;
            return (
              <div
                key={step}
                className="relative overflow-hidden rounded-full border border-gray-200 px-3 py-2 text-center text-xs font-black text-gray-400"
              >
                {on && (
                  <motion.span
                    layoutId={`step-${index}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="absolute inset-0 bg-gradient-to-r from-og-green-200 via-og-green-200 to-og-green-400"
                  />
                )}
                <span className={`relative ${on ? "text-interactive" : ""}`}>
                  {step.replace("_", " ")}
                </span>
              </div>
            );
          })}
        </div>

        <AnimatePresence>
          {msg && (
            <motion.p
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mb-4 rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700"
            >
              {msg}
            </motion.p>
          )}
          {anyErr && (
            <motion.p
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mb-4 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700"
            >
              {anyErr}
            </motion.p>
          )}
        </AnimatePresence>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
          <section className="rounded-[var(--radius-lg)] border border-gray-200 bg-white p-4 shadow-card">
            <input
              ref={titleRef}
              defaultValue={cp.title}
              disabled={!editable}
              className="w-full rounded-[var(--radius-md)] border-0 bg-gray-50 px-5 py-4 text-2xl font-black text-gray-950 outline-none focus:ring-4 focus:ring-gray-200 disabled:opacity-60"
            />
            <textarea
              ref={bodyRef}
              defaultValue={cp.body}
              disabled={!editable}
              rows={18}
              className="mt-3 w-full resize-y rounded-[var(--radius-md)] border border-gray-500 bg-white p-5 font-mono text-sm leading-6 text-gray-800 outline-none focus:border-gray-700 disabled:opacity-60"
            />
            <div className="mt-4 flex flex-wrap gap-2">
              <Button onClick={onSave} loading={update.isPending} size="sm">
                Save
              </Button>
              {(NEXT[cp.status] ?? []).map((t) => (
                <Button
                  key={t.to}
                  variant="secondary"
                  size="sm"
                  onClick={() => transition.mutate(t.to)}
                  disabled={transition.isPending}
                >
                  {t.label}
                </Button>
              ))}
              <Button variant="ghost" size="sm" onClick={onExport}>
                Export .md
              </Button>
            </div>
          </section>

          <aside className="space-y-4">
            <section className="rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card">
              <h2 className="text-sm font-black text-gray-900">Planning</h2>
              <div className="mt-4 space-y-3">
                <Field label="Next action">
                  <input
                    ref={nextActionRef}
                    defaultValue={cp.next_action ?? ""}
                    placeholder="Next action"
                    className={fieldCls}
                  />
                </Field>
                <Field label="Due date">
                  <input
                    ref={dueAtRef}
                    type="datetime-local"
                    defaultValue={toDateTimeLocal(cp.due_at)}
                    className={fieldCls}
                  />
                </Field>
              </div>
            </section>
            {lineage.length > 0 && (
              <section className="rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card">
                <h2 className="text-sm font-black text-gray-900">Lineage</h2>
                <div className="mt-4 space-y-3">
                  {lineage.map((row) => (
                    <div
                      key={row.key}
                      className="rounded-[var(--radius-md)] border border-gray-100 bg-gray-50 px-3 py-3"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-black uppercase text-gray-500">
                          {row.label}
                        </span>
                        <StatusBadge status={row.status} />
                      </div>
                      <p className="mt-1 font-mono text-xs font-semibold text-gray-400">
                        {shortId(row.id)}
                      </p>
                      {row.brief && (
                        <p className="mt-2 line-clamp-2 text-xs font-medium text-gray-500">
                          {row.brief}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}
            <GitHubPublishPanel content={cp} slug={tenantSlug} onMessage={setMsg} />
          </aside>
        </div>
      </section>
    </AppShell>
  );
}

function toDateTimeLocal(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toISOString().slice(0, 16);
}
