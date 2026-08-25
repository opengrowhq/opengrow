"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { appRootPath } from "@/lib/app-routes.mjs";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { BrandMark, GradientMesh, SparkIcon } from "@/components/illustrations";
import { EASE } from "@/components/motion";
import { useAcceptInvite } from "../hooks";

export function AcceptInviteForm({ token }: { token: string }) {
  const router = useRouter();
  const accept = useAcceptInvite();
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    accept.mutate(
      { token, displayName, password },
      {
        onSuccess: (me) => router.push(appRootPath(me.tenant_slug)),
      },
    );
  }

  return (
    <main className="grid min-h-screen bg-white lg:grid-cols-2">
      {/* Form side */}
      <div className="flex items-center justify-center p-6 sm:p-10">
        <motion.form
          onSubmit={onSubmit}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: EASE }}
          className="w-full max-w-sm"
        >
          <div className="mb-8 flex items-center gap-2.5">
            <BrandMark className="h-10 w-10" />
            <span className="text-xl font-black tracking-tight">OpenGrow</span>
          </div>

          <h1 className="text-3xl font-black tracking-tight">You&rsquo;re invited</h1>
          <p className="mt-2 text-sm font-medium text-gray-500">
            Set your name and password to join the workspace.
          </p>

          <div className="mt-8 space-y-4">
            <Field label="Your name">
              <Input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                autoComplete="name"
              />
            </Field>
            <Field label="Password">
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </Field>

            {accept.isError && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-xl bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-600"
              >
                {accept.error instanceof Error ? accept.error.message : "Could not accept invite"}
              </motion.p>
            )}

            <Button type="submit" size="lg" loading={accept.isPending} className="w-full">
              {accept.isPending ? "Joining…" : "Join workspace"}
            </Button>
          </div>
        </motion.form>
      </div>

      {/* Art side */}
      <div className="relative hidden overflow-hidden bg-gray-950 lg:block">
        <GradientMesh className="absolute inset-0 h-full w-full opacity-80" />
        <div className="relative flex h-full flex-col justify-between p-12 text-white">
          <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-white/80">
            <SparkIcon className="h-4 w-4" /> AI for Marketing
          </div>
          <div>
            <motion.h2
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: EASE, delay: 0.15 }}
              className="max-w-md text-4xl font-black leading-tight"
            >
              Launch 10x more content, 75% faster.
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: EASE, delay: 0.3 }}
              className="mt-4 max-w-md text-lg font-medium text-white/80"
            >
              Turn your brand into launch-ready ads, emails, and social posts — generated while you
              sleep.
            </motion.p>
          </div>
        </div>
      </div>
    </main>
  );
}
