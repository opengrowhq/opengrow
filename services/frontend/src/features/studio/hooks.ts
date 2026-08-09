"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  type Asset,
  type Generation,
  createGeneration,
  getAsset,
  getGeneration,
  uploadAsset,
} from "./api";

const TERMINAL_ASSET = ["INDEXED", "EMBED_FAILED", "SCAN_FAILED"];
const TERMINAL_GEN = ["COMPLETE", "FAILED"];

export function useUploadAsset() {
  return useMutation({ mutationFn: (file: File) => uploadAsset(file) });
}

export function useAsset(id: string | null) {
  return useQuery({
    queryKey: ["asset", id],
    queryFn: () => getAsset(id as string),
    enabled: !!id,
    // Poll until terminal, then stop — replaces the hand-rolled setTimeout loop.
    refetchInterval: (q) => {
      const s = (q.state.data as Asset | undefined)?.status;
      return s && TERMINAL_ASSET.includes(s) ? false : 1500;
    },
  });
}

export function useCreateGeneration() {
  return useMutation({
    mutationFn: (vars: { brief: string; referenceAssetId?: string }) =>
      createGeneration(vars.brief, vars.referenceAssetId),
  });
}

export function useGeneration(id: string | null) {
  return useQuery({
    queryKey: ["generation", id],
    queryFn: () => getGeneration(id as string),
    enabled: !!id,
    refetchInterval: (q) => {
      const s = (q.state.data as Generation | undefined)?.status;
      return s && TERMINAL_GEN.includes(s) ? false : 1500;
    },
  });
}
