"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { resolvePostAuthPath } from "@/lib/app-routes.mjs";
import { saveToken, saveTokenPair } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { BrandMark, GradientMesh, SparkIcon } from "@/components/illustrations";
import { EASE } from "@/components/motion";
import { fetchMe } from "../api";
import { GOOGLE_LOGIN_URL, isGoogleLoginAvailable, parseOAuthFragment } from "../oauth";
import { useLogin } from "../hooks";

function GoogleMark() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.5 12.27c0-.85-.08-1.66-.22-2.45H12v4.64h6.45a5.52 5.52 0 0 1-2.4 3.62v3h3.88c2.27-2.09 3.57-5.17 3.57-8.81Z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.96-1.07 7.94-2.92l-3.88-3c-1.08.72-2.45 1.15-4.06 1.15-3.12 0-5.77-2.11-6.71-4.95H1.29v3.1A12 12 0 0 0 12 24Z"
      />
      <path
        fill="#FBBC05"
        d="M5.29 14.28A7.2 7.2 0 0 1 4.9 12c0-.79.14-1.56.38-2.28v-3.1H1.29a12 12 0 0 0 0 10.76l4-3.1Z"
      />
      <path
        fill="#EA4335"
        d="M12 4.77c1.76 0 3.34.6 4.58 1.8l3.44-3.44A11.98 11.98 0 0 0 12 0 12 12 0 0 0 1.29 6.62l4 3.1C6.23 6.88 8.88 4.77 12 4.77Z"
      />
    </svg>
  );
}

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const login = useLogin();
  const [email, setEmail] = useState("demo@opengrow.dev");
  const [password, setPassword] = useState("");
  const [oauthError, setOauthError] = useState<string | null>(() =>
    typeof window !== "undefined" && new URLSearchParams(window.location.search).get("error")
      ? "Google sign-in failed. Please try again."
      : null,
  );

  // OAuth callback handoff: the hosted backend redirects back to
  // /login#access_token=…&refresh_token=… (fragment, so tokens never hit
  // server logs). Consume it once, strip the hash, land in the workspace.
  useEffect(() => {
    const pair = parseOAuthFragment(window.location.hash);
    if (pair) {
      if (pair.refresh_token) saveTokenPair(pair.access_token, pair.refresh_token);
      else saveToken(pair.access_token);
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
      void fetchMe()
        .then((me) => router.push(resolvePostAuthPath(next, me.tenant_slug)))
        .catch(() => setOauthError("Sign-in failed. Please try again."));
    }
    // Runs once on mount; `next` is captured from the initial URL.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const google = useQuery({
    queryKey: ["auth", "google-available"],
    queryFn: isGoogleLoginAvailable,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    login.mutate(
      { email, password },
      {
        onSuccess: (me) => router.push(resolvePostAuthPath(next, me.tenant_slug)),
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

          <h1 className="text-3xl font-black tracking-tight">
            {next ? "You're all set 🎉" : "Welcome back"}
          </h1>
          <p className="mt-2 text-sm font-medium text-gray-500">
            {next ? "Sign in to finish setting up your brand." : "Sign in to your workspace."}
          </p>

          <div className="mt-8 space-y-4">
            {google.data === true && (
              <>
                <a
                  href={GOOGLE_LOGIN_URL}
                  className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white text-sm font-bold text-gray-700 transition hover:bg-gray-50"
                >
                  <GoogleMark /> Continue with Google
                </a>
                <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
                  <span className="h-px flex-1 bg-gray-200" /> or <span className="h-px flex-1 bg-gray-200" />
                </div>
              </>
            )}

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
                autoComplete="current-password"
              />
            </Field>

            {(login.isError || oauthError) && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-xl bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-600"
              >
                {oauthError ??
                  (login.error instanceof Error ? login.error.message : "Login failed")}
              </motion.p>
            )}

            <Button type="submit" size="lg" loading={login.isPending} className="w-full">
              {login.isPending ? "Signing in…" : "Sign in"}
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
