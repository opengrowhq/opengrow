"use client";

import type { FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import type { defaultArticleBrief } from "../article-brief.mjs";

export type ArticleBriefValues = ReturnType<typeof defaultArticleBrief>;
export type ArticleBriefErrors = Partial<Record<keyof ArticleBriefValues, string>>;

export function ArticleBriefForm({
  brief,
  errors,
  onChange,
  onSubmit,
  pending,
}: {
  brief: ArticleBriefValues;
  errors: ArticleBriefErrors;
  onChange: (patch: Partial<ArticleBriefValues>) => void;
  onSubmit: () => void;
  pending: boolean;
}) {
  function submit(e: FormEvent) {
    e.preventDefault();
    onSubmit();
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Topic" htmlFor="brief-topic" error={errors.topic}>
        <Input
          id="brief-topic"
          value={brief.topic}
          onChange={(e) => onChange({ topic: e.target.value })}
          placeholder="e.g. Why founders should blog in 2026"
          aria-invalid={!!errors.topic}
        />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Primary keyword" htmlFor="brief-primary-keyword">
          <Input
            id="brief-primary-keyword"
            value={brief.primary_keyword}
            onChange={(e) => onChange({ primary_keyword: e.target.value })}
            placeholder="founder blogging"
          />
        </Field>
        <Field
          label="Secondary keywords"
          htmlFor="brief-secondary-keywords"
          hint="Comma-separated."
        >
          <Input
            id="brief-secondary-keywords"
            value={brief.secondary_keywords}
            onChange={(e) => onChange({ secondary_keywords: e.target.value })}
            placeholder="seo, content marketing"
          />
        </Field>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Audience" htmlFor="brief-audience">
          <Input
            id="brief-audience"
            value={brief.audience}
            onChange={(e) => onChange({ audience: e.target.value })}
            placeholder="Early-stage founders"
          />
        </Field>
        <Field label="Goal" htmlFor="brief-goal">
          <Select
            id="brief-goal"
            value={brief.goal}
            onChange={(e) => onChange({ goal: e.target.value })}
          >
            <option value="educate">Educate</option>
            <option value="compare">Compare</option>
            <option value="convert">Convert</option>
          </Select>
        </Field>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Tone" htmlFor="brief-tone">
          <Input
            id="brief-tone"
            value={brief.tone}
            onChange={(e) => onChange({ tone: e.target.value })}
            placeholder="Confident, plain-spoken"
          />
        </Field>
        <Field label="Length (words)" htmlFor="brief-length" error={errors.length_words}>
          <Input
            id="brief-length"
            type="number"
            min={200}
            max={10000}
            value={brief.length_words}
            onChange={(e) => onChange({ length_words: Number(e.target.value) })}
            aria-invalid={!!errors.length_words}
          />
        </Field>
        <Field label="Sections (target)" htmlFor="brief-sections" error={errors.sections_target}>
          <Input
            id="brief-sections"
            type="number"
            min={1}
            max={15}
            value={brief.sections_target}
            onChange={(e) => onChange({ sections_target: Number(e.target.value) })}
            aria-invalid={!!errors.sections_target}
          />
        </Field>
      </div>
      <Field label="Notes" htmlFor="brief-notes" hint="Angle, sources, things to avoid.">
        <Textarea
          id="brief-notes"
          rows={3}
          value={brief.notes}
          onChange={(e) => onChange({ notes: e.target.value })}
          placeholder="Anything the writer should know…"
        />
      </Field>
      <details className="rounded-[var(--radius-md)] border border-gray-100 bg-gray-50 px-3 py-2">
        <summary className="cursor-pointer text-xs font-black text-gray-600">
          Publishing details
        </summary>
        <div className="mt-3 space-y-3">
          <Field label="Slug" htmlFor="brief-slug" hint="Leave blank to derive it from the topic.">
            <Input
              id="brief-slug"
              value={brief.slug}
              onChange={(e) => onChange({ slug: e.target.value })}
              placeholder="why-founders-blog"
            />
          </Field>
          <Field label="Description" htmlFor="brief-description">
            <Textarea
              id="brief-description"
              rows={2}
              value={brief.description}
              onChange={(e) => onChange({ description: e.target.value })}
              placeholder="Meta description for the published piece."
            />
          </Field>
          <Field label="Tags" htmlFor="brief-tags" hint="Comma-separated.">
            <Input
              id="brief-tags"
              value={brief.tags}
              onChange={(e) => onChange({ tags: e.target.value })}
              placeholder="seo, founders"
            />
          </Field>
        </div>
      </details>
      <Button type="submit" loading={pending} className="w-full">
        Plan article
      </Button>
    </form>
  );
}
