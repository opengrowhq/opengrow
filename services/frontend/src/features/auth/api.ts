import { API_BASE, apiGet, parse } from "@/lib/http";

export type Me = {
  id: string;
  email: string;
  display_name: string;
  tenant_id: string;
  tenant_slug: string;
};

// The login endpoint uses OAuth2PasswordRequestForm → form-encoded fields.
export type TokenPair = { access_token: string; refresh_token: string };

export async function login(email: string, password: string): Promise<TokenPair> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  return parse<TokenPair>(res);
}

export function fetchMe(): Promise<Me> {
  return apiGet<Me>("/auth/me");
}

