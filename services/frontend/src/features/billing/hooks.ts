"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { loadToken } from "@/lib/auth";
import { createCheckout, createPortalSession, getSubscription } from "./api";

const hasToken = () => !!loadToken();

export function useSubscription() {
  return useQuery({
    queryKey: ["billing", "subscription"],
    queryFn: getSubscription,
    enabled: hasToken(),
  });
}

export function useCreateCheckout() {
  return useMutation({ mutationFn: createCheckout });
}

export function useCreatePortalSession() {
  return useMutation({ mutationFn: createPortalSession });
}
