import { API_BASE, apiGet, apiSend, parse } from "@/lib/http";

export type Me = {
  id: string;
  email: string;
  display_name: string;
  tenant_id: string;
  tenant_slug: string;
};

// The login endpoint uses OAuth2PasswordRequestForm → form-encoded fields.
export async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  const data = await parse<{ access_token: string }>(res);
  return data.access_token;
}

export function fetchMe(): Promise<Me> {
  return apiGet<Me>("/auth/me");
}

export type SignupInput = {
  email: string;
  password: string;
  display_name: string;
  tenant_name: string;
};

// Hosted-only — this endpoint doesn't exist in lite mode (no self-hosted
// self-service signup); a lite deployment 404s on this call.
export function signup(input: SignupInput): Promise<{ access_token: string }> {
  return apiSend<{ access_token: string }>("/auth/signup", "POST", input);
}
