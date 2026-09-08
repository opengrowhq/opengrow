// Two auth transports, selected by deployment shape:
//  - Lite (browser → fastapi-core directly): Bearer tokens in localStorage.
//  - Production (browser → node-gateway BFF): the gateway moves tokens into
//    httpOnly Secure SameSite=Strict cookies and strips them from response
//    bodies; JS never sees them. The gateway flags this with the
//    `x-og-auth: cookie` response header (see services/node-gateway).
"use client";

const KEY = "opengrow.token";
const REFRESH_KEY = "opengrow.refresh";

let cookieMode = false;

/** Mark this deployment as cookie-mode (gateway sets httpOnly cookies). */
export function setCookieMode(): void {
  if (cookieMode) return;
  cookieMode = true;
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("opengrow:auth"));
  }
}

export function isCookieMode(): boolean {
  return cookieMode;
}

/** True when a session exists under either transport. */
export function hasSession(): boolean {
  return cookieMode || !!loadToken();
}

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
