"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import { appRootPath } from "@/lib/app-routes.mjs";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { BrandMark, GradientMesh, SparkIcon } from "@/components/illustrations";
import { EASE } from "@/components/motion";
import { useSignup } from "../hooks";

export function SignupForm() {
  const router = useRouter();
  const signup = useSignup();
  const [tenantName, setTenantName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    signup.mutate(
      {
        tenant_name: tenantName,
        display_name: displayName,
        email,
        password,
      },
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

          <h1 className="text-3xl font-black tracking-tight">Create your workspace</h1>
          <p className="mt-2 text-sm font-medium text-gray-500">
            Free to start — upgrade to Pro or Team whenever you're ready.
          </p>

          <div className="mt-8 space-y-4">
            <Field label="Workspace name">
              <Input
                type="text"
                value={tenantName}
                onChange={(e) => setTenantName(e.target.value)}
                required
                autoComplete="organization"
                placeholder="Acme Inc"
              />
            </Field>
            <Field label="Your name">
              <Input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                autoComplete="name"
              />
            </Field>
            <Field label="Email">
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
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

            {signup.isError && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-xl bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-600"
              >
                {signup.error instanceof Error ? signup.error.message : "Signup failed"}
              </motion.p>
            )}

            <Button type="submit" size="lg" loading={signup.isPending} className="w-full">
              {signup.isPending ? "Creating workspace…" : "Create workspace"}
            </Button>

            <p className="text-center text-sm font-medium text-gray-500">
              Already have a workspace?{" "}
              <a href="/login" className="font-bold text-og-green-700 hover:underline">
                Sign in
              </a>
            </p>
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
          <div className="flex items-center gap-3 text-sm font-bold text-white/80">
            <span className="-space-x-2">
              {["A", "K", "M", "D"].map((a, i) => (
                <span
                  key={a}
                  className={`inline-flex h-7 w-7 items-center justify-center rounded-full border-2 border-gray-950 text-xs ${
                    ["bg-og-green-950", "bg-og-green-600", "bg-og-green-400", "bg-og-green-200"][i]
                  }`}
                >
                  {a}
                </span>
              ))}
            </span>
            4.9/5 from 4,268 customers
          </div>
        </div>
      </div>
    </main>
  );
}
