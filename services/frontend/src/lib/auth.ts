// Scaffold-grade token storage. Uses localStorage for now; a later phase moves
// this to an httpOnly cookie set by the node-gateway BFF (see BUILD-PLAN).
"use client";

const KEY = "opengrow.token";
const REFRESH_KEY = "opengrow.refresh";

export function saveToken(token: string): void {
  localStorage.setItem(KEY, token);
  window.dispatchEvent(new Event("opengrow:auth"));
}

export function saveTokenPair(accessToken: string, refreshToken: string): void {
  localStorage.setItem(KEY, accessToken);
  localStorage.setItem(REFRESH_KEY, refreshToken);
  window.dispatchEvent(new Event("opengrow:auth"));
}

export function loadRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function loadToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(KEY);
}

export function clearToken(): void {
  localStorage.removeItem(KEY);
  localStorage.removeItem(REFRESH_KEY);
  window.dispatchEvent(new Event("opengrow:auth"));
}
