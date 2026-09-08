import { isCookieMode } from "@/lib/auth";
import { API_BASE, apiGet, parse, readAuthMode } from "@/lib/http";

export type Me = {
  id: string;
  email: string;
  display_name: string;
  tenant_id: string;
  tenant_slug: string;
};

// The login endpoint uses OAuth2PasswordRequestForm → form-encoded fields.
export type TokenPair = { access_token: string; refresh_token: string };

/**
 * Logs in. Through the gateway the token pair is stripped from the body and
 * delivered as httpOnly cookies instead — then `pair` is null and the session
 * rides the cookies. In lite mode the pair is returned as before.
 */
export async function login(
  email: string,
  password: string,
): Promise<{ pair: TokenPair | null }> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  readAuthMode(res);
  if (isCookieMode()) {
    if (!res.ok) await parse<never>(res); // throws ApiError with the server detail
    return { pair: null };
  }
  return { pair: await parse<TokenPair>(res) };
}

export function fetchMe(): Promise<Me> {
  return apiGet<Me>("/auth/me");
}

