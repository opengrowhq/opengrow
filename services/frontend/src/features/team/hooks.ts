"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { loadToken, saveToken } from "@/lib/auth";
import {
  acceptInvite,
  createInvite,
  listInvites,
  listMembers,
  revokeInvite,
} from "./api";
import { fetchMe } from "@/features/auth/api";

const hasToken = () => !!loadToken();

export function useMembers() {
  return useQuery({ queryKey: ["team", "members"], queryFn: listMembers, enabled: hasToken() });
}

export function useInvites() {
  return useQuery({ queryKey: ["team", "invites"], queryFn: listInvites, enabled: hasToken() });
}

export function useCreateInvite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ email, role }: { email: string; role?: "member" | "admin" }) =>
      createInvite(email, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["team", "invites"] }),
  });
}

export function useRevokeInvite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteId: string) => revokeInvite(inviteId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["team", "invites"] }),
  });
}

export function useAcceptInvite() {
  return useMutation({
    mutationFn: async (vars: { token: string; displayName: string; password: string }) => {
      const { access_token } = await acceptInvite({
        token: vars.token,
        display_name: vars.displayName,
        password: vars.password,
      });
      saveToken(access_token);
      return fetchMe();
    },
  });
}
