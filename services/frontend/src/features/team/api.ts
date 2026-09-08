import { isCookieMode } from "@/lib/auth";
import { API_BASE, apiDelete, apiGet, apiSend, parse, readAuthMode } from "@/lib/http";

export type Invite = {
  id: string;
  email: string;
  role: string;
  status: string;
  expires_at: string;
};

export type Member = {
  id: string;
  email: string;
  display_name: string;
};

export const listMembers = () => apiGet<Member[]>("/invites/members");

export const listInvites = () => apiGet<Invite[]>("/invites");

export const createInvite = (email: string, role: "member" | "admin" = "member") =>
  apiSend<Invite>("/invites", "POST", { email, role });

export const revokeInvite = (inviteId: string) => apiDelete(`/invites/${inviteId}`);

export const removeMember = (userId: string) => apiDelete(`/invites/members/${userId}`);

export type AcceptInviteInput = {
  token: string;
  display_name: string;
  password: string;
};

/**
 * Accepts an invite. Through the gateway the returned token pair is stripped
 * from the body and set as httpOnly cookies instead — then `pair` is null.
 */
export async function acceptInvite(
  input: AcceptInviteInput,
): Promise<{ pair: { access_token: string; refresh_token?: string } | null }> {
  const res = await fetch(`${API_BASE}/invites/${input.token}/accept`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: input.display_name, password: input.password }),
  });
  readAuthMode(res);
  if (isCookieMode()) {
    if (!res.ok) await parse<never>(res); // throws ApiError with the server detail
    return { pair: null };
  }
  return { pair: await parse(res) };
}
