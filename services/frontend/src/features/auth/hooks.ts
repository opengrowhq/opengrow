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
      const { pair } = await login(vars.email, vars.password);
      // Cookie mode: the gateway already set httpOnly cookies (readAuthMode in
      // login() flagged it); nothing may be saved to localStorage. Only a
      // real (lite-mode) pair goes into storage.
      if (pair) saveTokenPair(pair.access_token, pair.refresh_token);
      return fetchMe();
    },
  });
}
