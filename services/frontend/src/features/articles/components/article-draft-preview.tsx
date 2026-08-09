"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/data-display";

export function ArticleDraftPreview({
  markdown,
  onSave,
  pending,
}: {
  markdown: string;
  onSave: () => void;
  pending: boolean;
}) {
  const words = markdown.split(/\s+/).filter(Boolean).length;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <Badge tone="info">{words.toLocaleString()} words</Badge>
        <Button onClick={onSave} loading={pending}>
          Save as content piece
        </Button>
      </div>
      <pre className="whitespace-pre-wrap rounded-[var(--radius-md)] border border-gray-100 bg-gray-50 p-4 font-sans text-sm font-medium leading-relaxed text-gray-800">
        {markdown}
      </pre>
    </div>
  );
}
