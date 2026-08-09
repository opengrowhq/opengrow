"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { StatusBadge, Badge } from "@/components/ui/data-display";
import { controlClass } from "@/components/ui/field";
import { appPath } from "@/lib/app-routes.mjs";
import { type ContentPiece, type Publication } from "../api";
import {
  useGitHubPublishConfig,
  usePublications,
  usePublishGithub,
  useRefreshPublication,
} from "../hooks";
import {
  cleanGitHubPublishForm,
  defaultGitHubPublishForm,
  loadLastUsed,
  saveLastUsed,
  validateGitHubPublishForm,
} from "../publish-form.mjs";

const fieldCls = controlClass("py-2.5 disabled:opacity-60");

const REFRESHABLE = new Set(["PR_OPENED", "FAILED", "PUBLISHING"]);

// The backend reuses one PR per content piece but writes a new Publication row
// each publish, so collapse to one row per PR (newest wins), newest-first.
function dedupePublications(list: Publication[]): Publication[] {
  const byKey = new Map<string, Publication>();
  for (const p of list) {
    const key = p.target?.pr_number != null ? `pr:${p.target.pr_number}` : `id:${p.id}`;
    const existing = byKey.get(key);
    if (
      !existing ||
      new Date(p.created_at).getTime() >= new Date(existing.created_at).getTime()
    ) {
      byKey.set(key, p);
    }
  }
  return Array.from(byKey.values()).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
}

function mergeLabel(p: Publication): { label: string; tone: "success" | "warning" | "info" } | null {
  if (p.target?.merged) return { label: "Merged", tone: "success" };
  if (p.target?.state === "closed") return { label: "Closed", tone: "warning" };
  if (p.status === "PR_OPENED") return { label: "Open", tone: "info" };
  return null;
}

function fmtDate(value: string): string {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString();
}

type PublishForm = ReturnType<typeof defaultGitHubPublishForm>;
type FieldErrors = Partial<Record<"repo" | "branch" | "base_branch" | "path", string>>;

export function GitHubPublishPanel({
  content,
  slug,
  onMessage,
}: {
  content: ContentPiece;
  slug?: string;
  onMessage: (message: string | null) => void;
}) {
  const publish = usePublishGithub(content.id);
  const refresh = useRefreshPublication(content.id);
  const configQuery = useGitHubPublishConfig();
  const pubsQuery = usePublications(content.id);
  const publishConfig = configQuery.data;
  const [publishForm, setPublishForm] = useState<PublishForm>(() =>
    defaultGitHubPublishForm(content, loadLastUsed(slug)),
  );
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  const configResolved = publishConfig !== undefined;
  const disabled = publishConfig?.configured === false;
  const canPublish =
    (content.status === "APPROVED" || content.status === "PUBLISHED") && !disabled;
  const publishBlockedReason =
    content.status !== "APPROVED" && content.status !== "PUBLISHED"
      ? "Approve this content before opening a GitHub PR."
      : null;
  const anyErr =
    (publish.error instanceof Error ? publish.error.message : null) ??
    (refresh.error instanceof Error ? refresh.error.message : null);

  const pubs = pubsQuery.data ? dedupePublications(pubsQuery.data) : [];
  const pubsResolved = pubsQuery.data !== undefined;

  function onPublish(e: FormEvent) {
    e.preventDefault();
    onMessage(null);
    const errors = validateGitHubPublishForm(publishForm) as FieldErrors;
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    publish.mutate(cleanGitHubPublishForm(publishForm), {
      onSuccess: (p) => {
        saveLastUsed(slug, {
          repo: publishForm.repo.trim(),
          base_branch: publishForm.base_branch.trim(),
        });
        const warns = p.target?.warnings;
        const warnSuffix = warns && warns.length ? ` — ${warns.join(" ")}` : "";
        onMessage(
          p.url ? `PR opened: ${p.url}${warnSuffix}` : `Publication ${p.status}`,
        );
      },
    });
  }

  function onRefresh(publicationId: string) {
    onMessage(null);
    refresh.mutate(publicationId, {
      onSuccess: (p) => {
        if (p.status === "PUBLISHED" || p.target?.merged) {
          onMessage("PR merged — content marked Published.");
        } else {
          onMessage(`Publication status: ${p.status}`);
        }
      },
    });
  }

  const set = (patch: Partial<PublishForm>) =>
    setPublishForm((form) => ({ ...form, ...patch }));

  const statusBadge = !configResolved ? (
    <Badge tone="info">CHECKING…</Badge>
  ) : (
    <Badge tone={disabled ? "warning" : "success"}>{disabled ? "DISABLED" : "READY"}</Badge>
  );

  return (
    <>
      <section className="rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-black text-gray-900">GitHub publish</h2>
            <p className="mt-1 text-xs font-medium text-gray-500">
              Opens a pull request with this Markdown file.
            </p>
            {publishConfig?.source === "tenant" && publishConfig.token_last4 && (
              <p className="mt-1 text-xs font-semibold text-gray-400">
                {publishConfig.display_name
                  ? `${publishConfig.display_name} ••••${publishConfig.token_last4}`
                  : `Workspace token ••••${publishConfig.token_last4}`}
              </p>
            )}
          </div>
          {statusBadge}
        </div>
        {configResolved && disabled && (
          <p className="mt-4 rounded-xl border border-amber-100 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700">
            GitHub publishing isn&apos;t connected.{" "}
            <Link href={appPath(slug, "settings")} className="underline">
              Connect GitHub in Settings
            </Link>
            .
          </p>
        )}
        {publishBlockedReason && (
          <p className="mt-4 rounded-xl border border-amber-100 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700">
            {publishBlockedReason}
          </p>
        )}
        {anyErr && (
          <p className="mt-4 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
            {anyErr}
          </p>
        )}
        <form onSubmit={onPublish} className="mt-4 space-y-3">
          <div>
            <input
              value={publishForm.repo}
              onChange={(e) => set({ repo: e.target.value })}
              placeholder="owner/repo"
              disabled={disabled}
              aria-invalid={!!fieldErrors.repo}
              className={fieldCls}
            />
            {fieldErrors.repo && (
              <p className="mt-1 text-xs font-semibold text-red-600">{fieldErrors.repo}</p>
            )}
          </div>
          <div>
            <input
              value={publishForm.path}
              onChange={(e) => set({ path: e.target.value })}
              placeholder="content/post.md"
              disabled={disabled}
              aria-invalid={!!fieldErrors.path}
              className={fieldCls}
            />
            {fieldErrors.path && (
              <p className="mt-1 text-xs font-semibold text-red-600">{fieldErrors.path}</p>
            )}
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <div>
              <input
                value={publishForm.base_branch}
                onChange={(e) => set({ base_branch: e.target.value })}
                placeholder="base: default"
                disabled={disabled}
                aria-invalid={!!fieldErrors.base_branch}
                className={fieldCls}
              />
              {fieldErrors.base_branch && (
                <p className="mt-1 text-xs font-semibold text-red-600">
                  {fieldErrors.base_branch}
                </p>
              )}
            </div>
            <div>
              <input
                value={publishForm.branch}
                onChange={(e) => set({ branch: e.target.value })}
                placeholder="opengrow/…"
                disabled={disabled}
                aria-invalid={!!fieldErrors.branch}
                className={fieldCls}
              />
              {fieldErrors.branch && (
                <p className="mt-1 text-xs font-semibold text-red-600">{fieldErrors.branch}</p>
              )}
            </div>
          </div>
          <details className="rounded-[var(--radius-md)] border border-gray-100 bg-gray-50 px-3 py-2">
            <summary className="cursor-pointer text-xs font-black text-gray-600">PR details</summary>
            <div className="mt-3 space-y-2">
              <label className="flex items-center gap-2 text-xs font-semibold text-gray-700">
                <input
                  type="checkbox"
                  checked={publishForm.draft}
                  onChange={(e) => set({ draft: e.target.checked })}
                  disabled={disabled}
                />
                Open as a draft PR
              </label>
              <input
                value={publishForm.labels}
                onChange={(e) => set({ labels: e.target.value })}
                placeholder="Labels (comma-separated)"
                disabled={disabled}
                className={fieldCls}
              />
              <input
                value={publishForm.reviewers}
                onChange={(e) => set({ reviewers: e.target.value })}
                placeholder="Reviewers (comma-separated usernames)"
                disabled={disabled}
                className={fieldCls}
              />
              <input
                value={publishForm.commit_message}
                onChange={(e) => set({ commit_message: e.target.value })}
                placeholder="Commit message"
                disabled={disabled}
                className={fieldCls}
              />
              <input
                value={publishForm.pr_title}
                onChange={(e) => set({ pr_title: e.target.value })}
                placeholder="PR title"
                disabled={disabled}
                className={fieldCls}
              />
              <textarea
                value={publishForm.pr_body}
                onChange={(e) => set({ pr_body: e.target.value })}
                placeholder="PR body"
                rows={3}
                disabled={disabled}
                className={`${fieldCls} resize-none`}
              />
            </div>
          </details>
          <Button type="submit" disabled={!canPublish || publish.isPending} className="w-full">
            Open PR
          </Button>
        </form>
      </section>

      <section className="rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card">
        <h2 className="text-sm font-black text-gray-900">Publications</h2>
        {!pubsResolved ? (
          <p className="mt-4 text-xs font-medium text-gray-400">Loading publications…</p>
        ) : pubs.length === 0 ? (
          <p className="mt-4 text-xs font-medium text-gray-400">
            No publications yet. Open a PR above to get started.
          </p>
        ) : (
          <ul className="mt-4 space-y-2 text-sm">
            {pubs.map((p) => {
              const merge = mergeLabel(p);
              return (
                <li
                  key={p.id}
                  className="rounded-[var(--radius-md)] border border-gray-100 bg-gray-50 p-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-bold">
                      {p.target?.pr_number != null ? `PR #${p.target.pr_number}` : p.channel}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {merge && <Badge tone={merge.tone}>{merge.label}</Badge>}
                      <StatusBadge status={p.status} />
                    </div>
                  </div>
                  {p.url ? (
                    <a
                      href={p.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 block truncate font-semibold text-interactive underline"
                    >
                      {p.external_ref ?? "PR"}
                    </a>
                  ) : (
                    <p className="mt-2 text-gray-500">{p.error_message ?? ""}</p>
                  )}
                  <p className="mt-1 text-xs text-gray-400">{fmtDate(p.created_at)}</p>
                  {REFRESHABLE.has(p.status) && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => onRefresh(p.id)}
                      disabled={refresh.isPending}
                      className="mt-3"
                    >
                      Refresh status
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </>
  );
}
