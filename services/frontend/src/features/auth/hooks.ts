"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { saveToken } from "@/lib/auth";
import { fetchMe, login, signup, type SignupInput } from "./api";

export function useMe(enabled = true) {
  return useQuery({ queryKey: ["me"], queryFn: fetchMe, enabled });
}

export function useLogin() {
  return useMutation({
    mutationFn: async (vars: { email: string; password: string }) => {
      const token = await login(vars.email, vars.password);
      saveToken(token);
      return fetchMe();
    },
  });
}

export function useSignup() {
  return useMutation({
    mutationFn: async (vars: SignupInput) => {
      const { access_token } = await signup(vars);
      saveToken(access_token);
      return fetchMe();
    },
  });
}
