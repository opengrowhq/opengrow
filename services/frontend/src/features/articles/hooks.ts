"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import type { Generation } from "@/features/studio/api";
import { loadToken } from "@/lib/auth";
import { createArticleGeneration, getArticleGeneration } from "./api";

const TERMINAL = ["COMPLETE", "FAILED"];

export function useCreateArticleGeneration() {
  return useMutation({ mutationFn: createArticleGeneration });
}

export function useArticleGeneration(id: string | null) {
  return useQuery({
    queryKey: ["generations", id],
    queryFn: () => getArticleGeneration(id as string),
    enabled: !!id && !!loadToken(),
    refetchInterval: (q) => {
      const s = (q.state.data as Generation | undefined)?.status;
      return s && TERMINAL.includes(s) ? false : 2000;
    },
  });
}
