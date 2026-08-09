"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { AppShell } from "@/components/ui/app-shell";
import { PageHeader } from "@/components/ui/page-header";
import { Button, ButtonLink } from "@/components/ui/button";
import { Textarea } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";
import { Skeleton } from "@/components/motion";
import { AdIcon, EmailIcon, SocialIcon, SparkIcon } from "@/components/illustrations";
import { useAuthGuard, useMe } from "@/features/auth";
import { useBrands } from "@/features/brand";
import { useCreateFromGeneration } from "@/features/content";
import { appPath } from "@/lib/app-routes.mjs";
import { CHANNEL_PRESETS, buildBrief, generatedTitle } from "../presets.mjs";
import { useAsset, useCreateGeneration, useGeneration, useUploadAsset } from "../hooks";

const ICONS: Record<string, (p: { className?: string }) => React.ReactNode> = {
  ads: AdIcon,
  socials: SocialIcon,
  emails: EmailIcon,
};

export function GeneratorStudio({ presetKey }: { presetKey: keyof typeof CHANNEL_PRESETS }) {
  const preset = CHANNEL_PRESETS[presetKey];
  const hasToken = useAuthGuard();
  const router = useRouter();
  const toast = useToast();
  const { data: me } = useMe(hasToken);
  const { data: brands } = useBrands();

  const upload = useUploadAsset();
  const [assetId, setAssetId] = useState<string | null>(null);
  const { data: asset } = useAsset(assetId);

  const createGen = useCreateGeneration();
  const [genId, setGenId] = useState<string | null>(null);
  const { data: gen } = useGeneration(genId);
  const saveContent = useCreateFromGeneration();

  const [brief, setBrief] = useState("");
  const tenantSlug = me?.tenant_slug;
  const Icon = ICONS[preset.icon] ?? SparkIcon;

  const generating =
    createGen.isPending || (!!genId && gen?.status !== "COMPLETE" && gen?.status !== "FAILED");
  const result = gen?.status === "COMPLETE" ? gen.result : null;
  const genError =
    gen?.status === "FAILED"
      ? gen.error_message || "Generation failed"
      : createGen.error instanceof Error
        ? createGen.error.message
        : null;
  const assetReady = asset?.status === "INDEXED";
  const hasBrand = !!brands?.length;

  function onGenerate() {
    if (!brief.trim()) return;
    createGen.mutate(
      { brief: buildBrief(preset, brief), referenceAssetId: assetId ?? undefined },
      { onSuccess: (g) => setGenId(g.id) },
    );
  }

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    upload.mutate(file, { onSuccess: (r) => setAssetId(r.asset_id) });
  }

  function onSave() {
    if (!genId) return;
    saveContent.mutate(
      { generationId: genId, title: generatedTitle(preset, brief) },
      {
        onSuccess: (cp) => {
          toast({ title: "Saved to Library", tone: "success" });
          router.push(appPath(tenantSlug, "content", cp.id));
        },
      },
    );
  }

  async function onCopy() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result);
      toast({ title: "Copied to clipboard", tone: "success" });
    } catch {
      toast({ title: "Couldn't copy", tone: "error" });
    }
  }

  return (
    <AppShell>
      <section>
        <PageHeader icon={Icon} title={preset.title} subtitle={preset.tagline} />

        {!hasBrand && (
          <div className="mt-6 flex items-center justify-between gap-4 rounded-[var(--radius-lg)] border border-amber-200 bg-amber-50 px-5 py-4">
            <p className="text-sm font-semibold text-amber-800">
              Add your brand first for on-brand results.
            </p>
            <ButtonLink href={appPath(tenantSlug, "onboarding")} variant="secondary" size="sm">
              Set up brand
            </ButtonLink>
          </div>
        )}

        {/* Composer */}
        <div className="mt-6 rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card">
          <Textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder={preset.placeholder}
            rows={4}
            className="text-base"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            {preset.examples.map((ex: string) => (
              <button
                key={ex}
                onClick={() => setBrief(ex)}
                className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-semibold text-gray-600 transition-colors hover:border-gray-300 hover:text-gray-900"
              >
                {ex}
              </button>
            ))}
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-gray-500 hover:text-gray-800">
              <input type="file" onChange={onFile} className="hidden" />
              <span className="flex h-8 items-center gap-2 rounded-full border border-gray-200 bg-white px-3">
                📎 {upload.isPending ? "Uploading…" : asset ? asset.filename : "Reference (optional)"}
              </span>
              {asset && (
                <span className={assetReady ? "text-emerald-700" : "text-amber-700"}>
                  {assetReady ? "indexed" : asset.status.toLowerCase()}
                </span>
              )}
            </label>
            <Button onClick={onGenerate} loading={generating} disabled={!brief.trim()}>
              <SparkIcon className="h-4 w-4" /> Generate
            </Button>
          </div>
        </div>

        {/* Result */}
        <AnimatePresence mode="wait">
          {generating && (
            <motion.div
              key="loading"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-6 rounded-[var(--radius-lg)] border border-gray-200 bg-white p-6 shadow-card"
            >
              <div className="flex items-center gap-2 text-sm font-bold text-gray-500">
                <SparkIcon className="h-4 w-4 animate-pulse" /> Generating your {preset.label.toLowerCase()}…
              </div>
              <div className="mt-4 space-y-3">
                {["100%", "90%", "95%", "70%", "85%"].map((w, i) => (
                  <Skeleton key={i} className="h-4" rounded="rounded-md" style={{ width: w }} />
                ))}
              </div>
            </motion.div>
          )}

          {!generating && genError && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-6 rounded-[var(--radius-lg)] border border-red-100 bg-red-50 p-6"
            >
              <p className="text-sm font-bold text-red-700">{genError}</p>
              <Button variant="secondary" size="sm" onClick={onGenerate} className="mt-4">
                Try again
              </Button>
            </motion.div>
          )}

          {!generating && result && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-6 rounded-[var(--radius-lg)] border border-gray-200 bg-white p-6 shadow-card"
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-black uppercase tracking-wide text-gray-400">
                  Generated {preset.label.toLowerCase()}
                </h2>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" onClick={onCopy}>
                    Copy
                  </Button>
                  <Button variant="secondary" size="sm" onClick={onGenerate}>
                    Regenerate
                  </Button>
                  <Button size="sm" onClick={onSave} loading={saveContent.isPending}>
                    Save to Library
                  </Button>
                </div>
              </div>
              <div className="whitespace-pre-wrap rounded-[var(--radius-md)] bg-gray-50 p-5 text-sm leading-7 text-gray-800">
                {result}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </section>
    </AppShell>
  );
}
