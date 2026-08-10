import { apiDelete, apiGet, apiSend } from "@/lib/http";

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

export type AcceptInviteInput = {
  token: string;
  display_name: string;
  password: string;
};

export const acceptInvite = (input: AcceptInviteInput) =>
  apiSend<{ access_token: string }>(`/invites/${input.token}/accept`, "POST", {
    display_name: input.display_name,
    password: input.password,
  });
