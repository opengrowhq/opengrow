"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { loadToken } from "@/lib/auth";

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
    () => !!loadToken(),
    () => false,
  );
}

/** Redirect to /login if there's no session token. */
export function useAuthGuard(): boolean {
  const router = useRouter();
  const hasToken = useHasToken();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const id = window.setTimeout(() => setChecked(true), 0);
    return () => window.clearTimeout(id);
  }, []);

  useEffect(() => {
    if (checked && !hasToken) router.replace("/login");
  }, [checked, hasToken, router]);

  return hasToken;
}
