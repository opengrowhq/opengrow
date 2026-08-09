// Scaffold-grade token storage. Uses localStorage for now; a later phase moves
// this to an httpOnly cookie set by the node-gateway BFF (see BUILD-PLAN).
"use client";

const KEY = "opengrow.token";

export function saveToken(token: string): void {
  localStorage.setItem(KEY, token);
  window.dispatchEvent(new Event("opengrow:auth"));
}

export function loadToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(KEY);
}

export function clearToken(): void {
  localStorage.removeItem(KEY);
  window.dispatchEvent(new Event("opengrow:auth"));
}
