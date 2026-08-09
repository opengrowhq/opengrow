import { apiGet, apiSend } from "@/lib/http";
import type { Generation } from "@/features/studio/api";

export const createArticleGeneration = (body: {
  brief: string;
  metadata: Record<string, unknown>;
  parent_generation_id?: string | null;
}) => apiSend<Generation>("/generations", "POST", body);

export const getArticleGeneration = (id: string) =>
  apiGet<Generation>(`/generations/${id}`);
