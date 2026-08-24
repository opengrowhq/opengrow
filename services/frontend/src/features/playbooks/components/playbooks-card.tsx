"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Badge } from "@/components/ui/data-display";
import { useActivatePlaybook, useCreatePlaybook, usePlaybooks } from "../hooks";
import type { PlaybookKind } from "../api";

const KIND_LABEL: Record<PlaybookKind, string> = {
  ARTICLE_OUTLINE: "Article outline",
  ARTICLE_DRAFT: "Article draft",
  GENERIC_COPY: "Generic copy",
};

export function PlaybooksCard() {
  const [kind, setKind] = useState<PlaybookKind>("ARTICLE_OUTLINE");
  const { data: playbooks, isLoading } = usePlaybooks(kind);
  const createPlaybook = useCreatePlaybook();
  const activatePlaybook = useActivatePlaybook();

  const [name, setName] = useState("");
  const [systemTemplate, setSystemTemplate] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setNotice(null);
    createPlaybook.mutate(
      { kind, name, system_template: systemTemplate },
      {
        onSuccess: () => {
          setName("");
          setSystemTemplate("");
          setNotice(`Saved "${name}" as a new version.`);
        },
      },
    );
  }

  const error =
    (createPlaybook.error instanceof Error ? createPlaybook.error.message : null) ??
    (activatePlaybook.error instanceof Error ? activatePlaybook.error.message : null);

  const versions = [...(playbooks ?? [])].sort((a, b) => b.version - a.version);

  return (
    <section className="rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card">
      <div>
        <h2 className="text-sm font-black text-gray-900">Playbooks</h2>
        <p className="mt-1 text-xs font-medium text-gray-500">
          Customize the methodology and writing rules used for generation.
        </p>
      </div>

      <div className="mt-4 max-w-xs">
        <Field label="Kind">
          <Select value={kind} onChange={(e) => setKind(e.target.value as PlaybookKind)}>
            {(Object.keys(KIND_LABEL) as PlaybookKind[]).map((k) => (
              <option key={k} value={k}>
                {KIND_LABEL[k]}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <form onSubmit={onCreate} className="mt-4 space-y-3">
        <Field label="Name">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="e.g. SEO-first outlines"
          />
        </Field>
        <Field label="System prompt">
          <Textarea
            value={systemTemplate}
            onChange={(e) => setSystemTemplate(e.target.value)}
            required
            rows={4}
            placeholder="You are a senior content strategist…"
          />
        </Field>
        <Button type="submit" loading={createPlaybook.isPending}>
          {createPlaybook.isPending ? "Saving…" : "Save new version"}
        </Button>
      </form>

      {notice && (
        <p className="mt-3 rounded-xl border border-green-100 bg-green-50 px-3 py-2 text-xs font-semibold text-green-700">
          {notice}
        </p>
      )}
      {error && (
        <p className="mt-3 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
          {error}
        </p>
      )}

      <div className="mt-6">
        <h3 className="text-xs font-black uppercase tracking-wide text-gray-500">
          Versions
        </h3>
        {isLoading && !playbooks && (
          <p className="mt-2 text-xs font-medium text-gray-400">Loading…</p>
        )}
        {!isLoading && versions.length === 0 && (
          <p className="mt-2 text-xs font-medium text-gray-400">
            No custom versions yet — generation uses the built-in default.
          </p>
        )}
        <ul className="mt-2 space-y-1">
          {versions.map((p) => (
            <li
              key={p.id}
              className="flex items-center justify-between gap-2 rounded-xl border border-gray-100 px-3 py-2 text-sm"
            >
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-900">{p.name}</span>
                <span className="text-xs font-medium text-gray-500">v{p.version}</span>
                {p.is_active && <Badge tone="success">Active</Badge>}
              </div>
              {!p.is_active && (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => activatePlaybook.mutate(p.id)}
                  loading={activatePlaybook.isPending}
                >
                  Activate
                </Button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
