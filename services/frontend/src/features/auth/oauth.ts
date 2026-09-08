// Google OAuth handoff helpers. The hosted backend (only) mounts
// /auth/google/login + /auth/google/callback; the core OSS deployment returns
// 404 there, in which case the login page simply doesn't render the button.
import { API_BASE } from "@/lib/http";

export const GOOGLE_LOGIN_URL = `${API_BASE}/auth/google/login`;

export type OAuthFragment = { access_token: string; refresh_token: string | null };

/** Parse the `#access_token=…&refresh_token=…` fragment the OAuth callback
 * redirects back with. Returns null when the hash carries no access token. */
export function parseOAuthFragment(hash: string): OAuthFragment | null {
  const raw = hash.startsWith("#") ? hash.slice(1) : hash;
  if (!raw) return null;
  const params = new URLSearchParams(raw);
  const access = params.get("access_token");
  if (!access) return null;
  return { access_token: access, refresh_token: params.get("refresh_token") };
}

/** True when the backend mounted the Google OAuth router. Enabled it answers
 * GET /auth/google/login with a 302 to Google; disabled (or unreachable) it
 * is a real 404. With redirect:"manual" a same-origin 302 surfaces as an
 * opaque-redirect response (status 0), so "anything that isn't a real 404"
 * means available. */
export async function isGoogleLoginAvailable(): Promise<boolean> {
  try {
    const res = await fetch(GOOGLE_LOGIN_URL, { redirect: "manual" });
    return res.status !== 404;
  } catch {
    return false;
  }
}
