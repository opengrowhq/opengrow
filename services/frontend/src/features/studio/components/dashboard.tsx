"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/ui/app-shell";
import { StatusPill } from "@/components/ui/status-pill";
import { useAuthGuard, useMe } from "@/features/auth";
import { useBrands } from "@/features/brand";
import { useCreateFromGeneration } from "@/features/content";
import { appPath, appRootPath } from "@/lib/app-routes.mjs";
import {
  useAsset,
  useCreateGeneration,
  useGeneration,
  useUploadAsset,
} from "../hooks";

export function Dashboard() {
  const hasToken = useAuthGuard();
  const router = useRouter();
  const { data: me } = useMe(hasToken);
  const { data: brands } = useBrands();

  const upload = useUploadAsset();
  const [assetId, setAssetId] = useState<string | null>(null);
  const { data: asset } = useAsset(assetId);

  const createGen = useCreateGeneration();
  const [genId, setGenId] = useState<string | null>(null);
  const { data: gen } = useGeneration(genId);

  const saveAsContent = useCreateFromGeneration();
  const [brief, setBrief] = useState(
    "Write a punchy launch tweet for an open-source AI content engine for founders.",
  );

  if (!me) {
    return (
      <AppShell>
        <div className="flex min-h-screen items-center justify-center text-sm text-gray-500">
          Loading...
        </div>
      </AppShell>
    );
  }

  const err =
    (upload.error instanceof Error ? upload.error.message : null) ??
    (createGen.error instanceof Error ? createGen.error.message : null) ??
    (saveAsContent.error instanceof Error ? saveAsContent.error.message : null);

  const hasBrand = !!brands?.length;
  const assetReady = asset?.status === "INDEXED";
  const canSave = gen?.status === "COMPLETE";
  const appHome = appRootPath(me.tenant_slug);
  const setup = [
    { label: "Brand DNA", href: appPath(me.tenant_slug, "brand") },
    { label: "Generate content", href: appHome },
    { label: "Save content", href: appPath(me.tenant_slug, "content") },
    { label: "Approve", href: appPath(me.tenant_slug, "content") },
    { label: "Open GitHub PR", href: appPath(me.tenant_slug, "content") },
  ];

  return (
    <AppShell>
      <section className="flex min-h-screen flex-col">
        <div className="mx-auto flex w-full max-w-[760px] flex-1 flex-col justify-center pb-10">
          <div className="mb-10 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-gray-200 bg-white text-xl shadow-sm">
              OG
            </div>
            <h1 className="text-3xl font-semibold tracking-normal text-gray-950 md:text-4xl">
              What are we growing today?
            </h1>
            <p className="mt-3 text-sm text-gray-500">
              {me.email} · tenant {me.tenant_id.slice(0, 8)}
            </p>
          </div>

          {err && (
            <p className="mb-4 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
              {err}
            </p>
          )}

          <div className="rounded-[28px] border border-gray-200 bg-white p-3 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
            <textarea
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              rows={4}
              className="block min-h-32 w-full resize-none rounded-3xl border-0 bg-transparent px-5 py-4 text-base text-gray-900 outline-none placeholder:text-gray-500"
              placeholder="Describe the content you want..."
            />
            <div className="flex flex-col gap-3 border-t border-gray-100 px-2 pt-3 sm:flex-row sm:items-center sm:justify-between">
              <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-4 text-sm font-medium text-gray-700 hover:bg-gray-100">
                <span className="text-base">+</span>
                Brand file
                <input
                  type="file"
                  className="sr-only"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      upload.mutate(file, {
                        onSuccess: (r) => setAssetId(r.asset_id),
                      });
                    }
                  }}
                />
              </label>
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  href={appPath(me.tenant_slug, "brand")}
                  className="rounded-full border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50"
                >
                  Brand
                </Link>
                <Link
                  href={appPath(me.tenant_slug, "content")}
                  className="rounded-full border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50"
                >
                  Library
                </Link>
                <button
                  onClick={() =>
                    createGen.mutate(
                      {
                        brief,
                        referenceAssetId: assetReady ? asset.id : undefined,
                      },
                      { onSuccess: (g) => setGenId(g.id) },
                    )
                  }
                  disabled={createGen.isPending || !brief.trim()}
                  className="rounded-full bg-interactive px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-interactive-hover disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Generate
                </button>
              </div>
            </div>
          </div>

          {asset && (
            <div className="mt-4 flex items-center justify-between rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm">
              <span className="truncate text-gray-700">{asset.filename}</span>
              <StatusPill status={asset.status} />
            </div>
          )}

          {gen && (
            <div className="mt-4 rounded-3xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-800">
                  Generation
                </span>
                <StatusPill status={gen.status} />
              </div>
              {gen.result && (
                <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-gray-700">
                  {gen.result}
                </p>
              )}
              {gen.error_message && (
                <p className="mt-4 text-sm text-red-600">{gen.error_message}</p>
              )}
              {canSave && (
                <button
                  onClick={() =>
                    saveAsContent.mutate(
                      { generationId: gen.id },
                      {
                        onSuccess: (cp) =>
                          router.push(appPath(me.tenant_slug, "content", cp.id)),
                      },
                    )
                  }
                  disabled={saveAsContent.isPending}
                  className="mt-5 rounded-full border border-gray-900 bg-gray-950 px-5 py-2 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-50"
                >
                  Save as content
                </button>
              )}
            </div>
          )}
        </div>

        <div className="grid gap-3 md:grid-cols-5">
          {setup.map((item, index) => {
            const done =
              (item.label === "Brand DNA" && hasBrand) ||
              (item.label === "Generate content" && !!gen) ||
              (item.label === "Save content" && canSave);
            return (
              <Link
                key={item.label}
                href={item.href}
                className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="flex items-center justify-between">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 text-xs font-semibold text-gray-600">
                    {index + 1}
                  </span>
                  <span
                    className={`h-2.5 w-2.5 rounded-full ${
                      done ? "bg-emerald-400" : "bg-gray-200"
                    }`}
                  />
                </div>
                <p className="mt-5 text-sm font-semibold text-gray-900">
                  {item.label}
                </p>
              </Link>
            );
          })}
        </div>
      </section>
    </AppShell>
  );
}
