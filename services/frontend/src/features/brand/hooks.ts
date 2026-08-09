"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { loadToken } from "@/lib/auth";
import {
  type Brand,
  type BrandProfile,
  createBrand,
  getBrand,
  listBrands,
  updateBrand,
} from "./api";

const hasToken = () => !!loadToken();
const TERMINAL = ["READY", "FAILED"];

export function useBrands() {
  return useQuery({
    queryKey: ["brands"],
    queryFn: listBrands,
    enabled: hasToken(),
  });
}

export function useBrand(id: string | null) {
  return useQuery({
    queryKey: ["brand", id],
    queryFn: () => getBrand(id as string),
    enabled: !!id && hasToken(),
    // Poll while the Brand DNA extraction runs; stop at READY/FAILED.
    refetchInterval: (q) => {
      const s = (q.state.data as Brand | undefined)?.status;
      return s && TERMINAL.includes(s) ? false : 1500;
    },
  });
}

export function useCreateBrand() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createBrand,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["brands"] }),
  });
}

export function useUpdateBrand(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: { name?: string; profile?: BrandProfile }) =>
      updateBrand(id, patch),
    onSuccess: (b) => {
      qc.setQueryData(["brand", id], b);
      qc.invalidateQueries({ queryKey: ["brands"] });
    },
  });
}
