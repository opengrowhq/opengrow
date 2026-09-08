"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { hasSession } from "@/lib/auth";
import { ensureSession } from "@/lib/http";

const AUTH_EVENT = "opengrow:auth";

function subscribe(callback: () => void) {
  if (typeof window === "undefined") return () => {};
  const initial = window.setTimeout(callback, 0);
  window.addEventListener("storage", callback);
  window.addEventListener(AUTH_EVENT, callback);
  return () => {
    window.clearTimeout(initial);
    window.removeEventListener("storage", callback);
    window.removeEventListener(AUTH_EVENT, callback);
  };
}

export function useHasToken(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => hasSession(),
    () => false,
  );
}

/** Redirect to /login if there's no session under either auth transport. */
export function useAuthGuard(): boolean {
  const router = useRouter();
  const hasToken = useHasToken();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const id = window.setTimeout(() => setChecked(true), 0);
    return () => window.clearTimeout(id);
  }, []);

  useEffect(() => {
    if (!checked || hasToken) return;
    let cancelled = false;
    // Cookie mode after a page reload: no localStorage token, but the og_rt
    // cookie may still yield a session. Only redirect when it doesn't.
    void ensureSession().then((restored) => {
      if (!cancelled && !restored) router.replace("/login");
    });
    return () => {
      cancelled = true;
    };
  }, [checked, hasToken, router]);

  return hasToken;
}
