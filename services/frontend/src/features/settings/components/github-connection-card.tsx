"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { Badge } from "@/components/ui/data-display";
import {
  useDeleteGitHubCredential,
  useGitHubPublishConfig,
  useUpsertGitHubCredential,
} from "@/features/content/hooks";
import {
  cleanGitHubCredentialInput,
  githubConnectionStatus,
  maskedToken,
} from "../github-connection.mjs";

const GITHUB_PAT_URL = "https://github.com/settings/personal-access-tokens";

export function GitHubConnectionCard() {
  const { data: config, isLoading } = useGitHubPublishConfig();
  const upsert = useUpsertGitHubCredential();
  const remove = useDeleteGitHubCredential();
  const [token, setToken] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [formErr, setFormErr] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  const status = githubConnectionStatus(config);
  const connectedName = config?.display_name ?? upsert.data?.display_name ?? null;
  const last4 = config?.token_last4 ?? upsert.data?.token_last4 ?? null;

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setNotice(null);
    const cleaned = cleanGitHubCredentialInput({ token, display_name: displayName });
    if (!cleaned.ok) {
      setFormErr(cleaned.error);
      return;
    }
    setFormErr(null);
    upsert.mutate(cleaned.body, {
      onSuccess: () => {
        setToken("");
        setNotice("GitHub connected. Pull requests will use this workspace token.");
      },
    });
  }

  function onDisconnect() {
    setNotice(null);
    remove.mutate(undefined, {
      onSuccess: () => {
        setConfirming(false);
        setNotice("Workspace token removed.");
      },
    });
  }

  const mutationErr =
    (upsert.error instanceof Error ? upsert.error.message : null) ??
    (remove.error instanceof Error ? remove.error.message : null);

  return (
    <section className="rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-black text-gray-900">GitHub connection</h2>
          <p className="mt-1 text-xs font-medium text-gray-500">
            Publishes approved content to your repo as pull requests.
          </p>
        </div>
        <Badge tone={status.tone}>{status.label.toUpperCase()}</Badge>
      </div>

      {isLoading && !config && (
        <p className="mt-4 text-xs font-medium text-gray-400">Checking connection…</p>
      )}

      {status.state === "workspace" && (
        <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">
          Connected with workspace token {maskedToken(last4)}
          {connectedName ? ` (${connectedName})` : ""}
        </div>
      )}
      {status.state === "instance" && (
        <p className="mt-4 rounded-xl border border-sky-100 bg-sky-50 px-3 py-2 text-xs font-semibold text-sky-700">
          Connected via the instance token. Add a workspace token below to publish with
          your own GitHub identity.
        </p>
      )}

      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <Field
          label="Personal access token"
          hint={
            <>
              Create a fine-grained token at{" "}
              <a
                href={GITHUB_PAT_URL}
                target="_blank"
                rel="noreferrer"
                className="font-semibold text-interactive underline"
              >
                github.com/settings/personal-access-tokens
              </a>{" "}
              with Contents (read/write) and Pull requests (read/write) on the target repos.
            </>
          }
        >
          <Input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="github_pat_…"
            autoComplete="off"
          />
        </Field>
        <Field label="Display name (optional)">
          <Input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g. Marketing site bot"
          />
        </Field>
        {(formErr ?? mutationErr) && (
          <p className="rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
            {formErr ?? mutationErr}
          </p>
        )}
        {notice && (
          <p className="rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">
            {notice}
          </p>
        )}
        <Button type="submit" loading={upsert.isPending} className="w-full">
          {upsert.isPending
            ? "Verifying token…"
            : config?.has_tenant_credential
              ? "Replace token"
              : "Connect GitHub"}
        </Button>
      </form>

      {config?.has_tenant_credential && (
        <div className="mt-4 border-t border-gray-100 pt-4">
          {confirming ? (
            <div className="flex flex-wrap items-center gap-2">
              <p className="w-full text-xs font-semibold text-gray-600">
                Remove the workspace token? Publishing falls back to the instance token if
                one is set.
              </p>
              <Button
                variant="danger"
                size="sm"
                onClick={onDisconnect}
                loading={remove.isPending}
              >
                Confirm disconnect
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setNotice(null);
                setConfirming(true);
              }}
            >
              Disconnect workspace token
            </Button>
          )}
        </div>
      )}
    </section>
  );
}
