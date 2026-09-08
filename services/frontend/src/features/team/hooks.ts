"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { hasSession, saveToken } from "@/lib/auth";
import {
  acceptInvite,
  createInvite,
  listInvites,
  listMembers,
  removeMember,
  revokeInvite,
} from "./api";
import { fetchMe } from "@/features/auth/api";

const hasToken = () => hasSession();

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

export function useRemoveMember() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => removeMember(userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["team", "members"] }),
  });
}

export function useAcceptInvite() {
  return useMutation({
    mutationFn: async (vars: { token: string; displayName: string; password: string }) => {
      const { pair } = await acceptInvite({
        token: vars.token,
        display_name: vars.displayName,
        password: vars.password,
      });
      // Cookie mode: gateway already set the httpOnly cookies — save nothing.
      if (pair) saveToken(pair.access_token);
      return fetchMe();
    },
  });
}
