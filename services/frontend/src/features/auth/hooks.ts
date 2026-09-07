"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { saveTokenPair } from "@/lib/auth";
import { fetchMe, login } from "./api";

export function useMe(enabled = true) {
  return useQuery({ queryKey: ["me"], queryFn: fetchMe, enabled });
}

export function useLogin() {
  return useMutation({
    mutationFn: async (vars: { email: string; password: string }) => {
      const pair = await login(vars.email, vars.password);
      saveTokenPair(pair.access_token, pair.refresh_token);
      return fetchMe();
    },
  });
}
