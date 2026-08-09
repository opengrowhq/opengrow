"use client";

import { useRef } from "react";
import { Button } from "@/components/ui/button";
import { Field, controlClass } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";
import { type Brand } from "../api";
import { useUpdateBrand } from "../hooks";

const asText = (v: unknown) => (typeof v === "string" ? v : v == null ? "" : String(v));
const asLines = (v: unknown) => (Array.isArray(v) ? v.map(String).join("\n") : asText(v));
const linesToArr = (s: string) => s.split("\n").map((x) => x.trim()).filter(Boolean);
const csvToArr = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

const inputCls = controlClass("py-3");

export function BrandProfileEditor({ brand, onSaved }: { brand: Brand; onSaved?: () => void }) {
  const update = useUpdateBrand(brand.id);
  const toast = useToast();
  const p = brand.profile ?? {};
  const tone = useRef<HTMLInputElement>(null);
  const tagline = useRef<HTMLInputElement>(null);
  const audience = useRef<HTMLInputElement>(null);
  const palette = useRef<HTMLInputElement>(null);
  const pains = useRef<HTMLTextAreaElement>(null);
  const doPhrases = useRef<HTMLTextAreaElement>(null);
  const dontPhrases = useRef<HTMLTextAreaElement>(null);

  function onSave() {
    update.mutate(
      {
        profile: {
          ...p,
          tone: tone.current?.value ?? "",
          tagline: tagline.current?.value ?? "",
          audience: audience.current?.value ?? "",
          palette: csvToArr(palette.current?.value ?? ""),
          pains: linesToArr(pains.current?.value ?? ""),
          do_phrases: linesToArr(doPhrases.current?.value ?? ""),
          dont_phrases: linesToArr(dontPhrases.current?.value ?? ""),
        },
      },
      {
        onSuccess: () => {
          toast({ title: "Brand saved", description: "Your brand DNA has been updated.", tone: "success" });
          onSaved?.();
        },
      },
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Tone">
          <input ref={tone} defaultValue={asText(p.tone)} className={inputCls} />
        </Field>
        <Field label="Tagline">
          <input ref={tagline} defaultValue={asText(p.tagline)} className={inputCls} />
        </Field>
      </div>
      <Field label="Audience">
        <input ref={audience} defaultValue={asText(p.audience)} className={inputCls} />
      </Field>
      <Field label="Palette (comma-separated hex)">
        <input
          ref={palette}
          defaultValue={Array.isArray(p.palette) ? p.palette.join(", ") : asText(p.palette)}
          placeholder="#111827, #6366f1"
          className={inputCls}
        />
      </Field>
      <Field label="Audience pains (one per line)">
        <textarea ref={pains} defaultValue={asLines(p.pains)} rows={3} className={`${inputCls} resize-y`} />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Do say (one per line)">
          <textarea ref={doPhrases} defaultValue={asLines(p.do_phrases)} rows={2} className={`${inputCls} resize-y`} />
        </Field>
        <Field label="Don't say (one per line)">
          <textarea ref={dontPhrases} defaultValue={asLines(p.dont_phrases)} rows={2} className={`${inputCls} resize-y`} />
        </Field>
      </div>

      <div className="flex items-center gap-3">
        <Button onClick={onSave} loading={update.isPending}>
          {update.isPending ? "Saving…" : "Save brand"}
        </Button>
        {update.isError && (
          <span className="text-sm font-semibold text-red-600">
            {update.error instanceof Error ? update.error.message : "Save failed"}
          </span>
        )}
      </div>
    </div>
  );
}
