"use client";

import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/field";
import { moveSection } from "../outline.mjs";

export type OutlineSection = { id: string; heading: string; points: string[] };

let sectionSeq = 0;
export function nextSectionId(): string {
  return `sec-${++sectionSeq}`;
}

export function ArticleOutlineEditor({
  sections,
  onChange,
  onRegenerate,
  onWriteDraft,
  writeLabel = "Write full draft",
  pending,
}: {
  sections: OutlineSection[];
  onChange: (sections: OutlineSection[]) => void;
  onRegenerate?: () => void;
  onWriteDraft: () => void;
  writeLabel?: string;
  pending: boolean;
}) {
  function update(index: number, patch: Partial<OutlineSection>) {
    onChange(sections.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  }

  return (
    <div className="space-y-3">
      {sections.map((section, i) => (
        <div
          key={section.id}
          className="rounded-[var(--radius-md)] border border-gray-100 bg-gray-50 p-3"
        >
          <div className="flex items-center gap-2">
            <span className="w-6 shrink-0 text-center text-xs font-black text-gray-400">
              {i + 1}
            </span>
            <Input
              aria-label={`Section ${i + 1} heading`}
              value={section.heading}
              onChange={(e) => update(i, { heading: e.target.value })}
              placeholder="Section heading"
            />
          </div>
          <Textarea
            aria-label={`Section ${i + 1} points`}
            className="mt-2"
            rows={3}
            value={section.points.join("\n")}
            onChange={(e) => update(i, { points: e.target.value.split("\n") })}
            placeholder="One talking point per line"
          />
          <div className="mt-2 flex gap-1.5">
            <Button
              variant="ghost"
              size="sm"
              aria-label={`Move section ${i + 1} up`}
              onClick={() => onChange(moveSection(sections, i, i - 1))}
              disabled={i === 0}
            >
              Move up
            </Button>
            <Button
              variant="ghost"
              size="sm"
              aria-label={`Move section ${i + 1} down`}
              onClick={() => onChange(moveSection(sections, i, i + 1))}
              disabled={i === sections.length - 1}
            >
              Move down
            </Button>
            <Button
              variant="ghost"
              size="sm"
              aria-label={`Remove section ${i + 1}`}
              onClick={() => onChange(sections.filter((_, idx) => idx !== i))}
            >
              Remove
            </Button>
          </div>
        </div>
      ))}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onChange([...sections, { id: nextSectionId(), heading: "", points: [] }])}
        >
          Add section
        </Button>
        {onRegenerate && (
          <Button variant="secondary" size="sm" onClick={onRegenerate} disabled={pending}>
            Regenerate outline
          </Button>
        )}
        <Button
          onClick={onWriteDraft}
          loading={pending}
          disabled={sections.length === 0 || pending}
          className="ml-auto"
        >
          {writeLabel}
        </Button>
      </div>
    </div>
  );
}
