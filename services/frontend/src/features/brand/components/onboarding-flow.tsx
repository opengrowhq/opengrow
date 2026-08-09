"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { BrandMark, GradientMesh } from "@/components/illustrations";
import { EASE } from "@/components/motion";
import { useAuthGuard, useMe } from "@/features/auth";
import { appRootPath } from "@/lib/app-routes.mjs";
import { useBrand, useCreateBrand } from "../hooks";
import { BrandProfileEditor } from "./brand-profile-editor";

const STEPS = [
  { key: "SCRAPING", label: "Reading your website" },
  { key: "EXTRACTING", label: "Learning your brand" },
  { key: "READY", label: "Ready" },
];
const ORDER = ["PENDING", "SCRAPING", "EXTRACTING", "READY"];

function Stepper({ status }: { status: string }) {
  const current = ORDER.indexOf(status);
  return (
    <ul className="space-y-3">
      {STEPS.map((s) => {
        const idx = ORDER.indexOf(s.key);
        const done = current > idx || status === "READY";
        const active = current === idx && status !== "READY";
        return (
          <li key={s.key} className="flex items-center gap-3 text-sm">
            <span
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-black transition-colors ${
                done
                  ? "bg-emerald-700 text-white"
                  : active
                    ? "bg-interactive text-white"
                    : "bg-gray-200 text-gray-500"
              }`}
            >
              {done ? "✓" : active ? "" : idx + 1}
              {active && (
                <span className="h-2 w-2 animate-pulse rounded-full bg-white" />
              )}
            </span>
            <span className={active || done ? "font-bold text-gray-900" : "font-medium text-gray-500"}>
              {s.label}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export function OnboardingFlow({ slug }: { slug?: string }) {
  const hasToken = useAuthGuard();
  const router = useRouter();
  const { data: me } = useMe(hasToken);
  const create = useCreateBrand();
  const [brandId, setBrandId] = useState<string | null>(null);
  const [manual, setManual] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const { data: brand } = useBrand(brandId);

  function onStart(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    create.mutate(
      { name: name.trim(), source_url: url.trim() || undefined },
      { onSuccess: (b) => setBrandId(b.id) },
    );
  }

  const inReview = brand && (brand.status === "READY" || manual);
  const appHome = appRootPath(me?.tenant_slug ?? slug);
  const stepIndex = inReview ? 2 : brandId ? 1 : 0;

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-white p-6">
      <GradientMesh className="absolute inset-0 h-full w-full opacity-40" />
      <div className="relative w-full max-w-lg">
        <header className="mb-6 text-center">
          <div className="mb-4 flex justify-center">
            <BrandMark className="h-12 w-12" />
          </div>
          <h1 className="text-3xl font-black tracking-tight">Welcome to OpenGrow</h1>
          <p className="mt-2 text-sm font-medium text-gray-500">Let&apos;s learn your brand.</p>
        </header>

        {/* Progress bar */}
        <div className="mb-6 flex gap-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-200">
              <motion.div
                className="h-full bg-grad"
                initial={false}
                animate={{ width: i <= stepIndex ? "100%" : "0%" }}
                transition={{ duration: 0.5, ease: EASE }}
              />
            </div>
          ))}
        </div>

        <div className="rounded-[var(--radius-lg)] border border-gray-200 bg-white/90 p-6 shadow-card backdrop-blur">
          <AnimatePresence mode="wait">
            {!brandId && (
              <motion.form
                key="start"
                onSubmit={onStart}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-4"
              >
                <Field label="Brand name">
                  <Input value={name} onChange={(e) => setName(e.target.value)} required />
                </Field>
                <Field
                  label={<>Website URL <span className="font-medium text-gray-400">(optional)</span></>}
                  hint="We'll read it to learn your tone, audience and style."
                >
                  <Input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://yourbrand.com"
                  />
                </Field>
                {create.isError && (
                  <p className="rounded-xl bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-600">
                    {create.error instanceof Error ? create.error.message : "Failed"}
                  </p>
                )}
                <Button type="submit" size="lg" loading={create.isPending} className="w-full">
                  {create.isPending ? "Starting…" : "Continue"}
                </Button>
              </motion.form>
            )}

            {brandId && !inReview && (
              <motion.div
                key="building"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-4"
              >
                <Stepper status={brand?.status ?? "PENDING"} />
                {brand?.status === "FAILED" && (
                  <div className="space-y-3">
                    <p className="rounded-xl bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-600">
                      Couldn&apos;t auto-learn your brand
                      {brand.error_message ? `: ${brand.error_message}` : ""}.
                    </p>
                    <Button variant="secondary" onClick={() => setManual(true)}>
                      Fill it in manually →
                    </Button>
                  </div>
                )}
              </motion.div>
            )}

            {inReview && brand && (
              <motion.div
                key="review"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-5"
              >
                <div>
                  <h2 className="text-lg font-black">Review your brand</h2>
                  <p className="text-sm font-medium text-gray-500">Tweak anything that looks off.</p>
                </div>
                <BrandProfileEditor brand={brand} />
                <Button size="lg" onClick={() => router.push(appHome)} className="w-full">
                  Finish — go to Studio
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <p className="mt-6 text-center text-sm">
          <Link href={appHome} className="font-semibold text-gray-500 hover:text-gray-900">
            Skip for now
          </Link>
        </p>
      </div>
    </main>
  );
}
