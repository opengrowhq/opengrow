"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { loadToken } from "@/lib/auth";
import {
  type ContentPatch,
  type PublishGitHubInput,
  createContent,
  createFromGeneration,
  deleteGitHubCredential,
  getGeneration,
  getGitHubPublishConfig,
  getContent,
  listContent,
  listPublications,
  publishGithub,
  refreshPublication,
  transitionContent,
  updateContent,
  upsertGitHubCredential,
} from "./api";

const hasToken = () => !!loadToken();

export function useContentList() {
  return useQuery({
    queryKey: ["content"],
    queryFn: listContent,
    enabled: hasToken(),
  });
}

export function useContent(id: string) {
  return useQuery({
    queryKey: ["content", id],
    queryFn: () => getContent(id),
    enabled: !!id && hasToken(),
  });
}

export function useGeneration(id: string | null | undefined) {
  return useQuery({
    queryKey: ["generation", id],
    queryFn: () => getGeneration(id as string),
    enabled: !!id && hasToken(),
  });
}

export function useCreateContent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createContent,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["content"] }),
  });
}

export function useCreateFromGeneration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { generationId: string; title?: string }) =>
      createFromGeneration(vars.generationId, vars.title),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["content"] }),
  });
}

export function useUpdateContent(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: ContentPatch) => updateContent(id, patch),
    onSuccess: (cp) => {
      qc.setQueryData(["content", id], cp);
      qc.invalidateQueries({ queryKey: ["content"] });
    },
  });
}

export function useTransitionContent(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (status: string) => transitionContent(id, status),
    onSuccess: (cp) => {
      qc.setQueryData(["content", id], cp);
      qc.invalidateQueries({ queryKey: ["content"] });
    },
  });
}

export function usePublications(id: string) {
  return useQuery({
    queryKey: ["publications", id],
    queryFn: () => listPublications(id),
    enabled: !!id && hasToken(),
  });
}

export function useGitHubPublishConfig() {
  return useQuery({
    queryKey: ["github-publish-config"],
    queryFn: getGitHubPublishConfig,
    enabled: hasToken(),
  });
}

export function useUpsertGitHubCredential() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: upsertGitHubCredential,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["github-publish-config"] }),
  });
}

export function useDeleteGitHubCredential() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteGitHubCredential,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["github-publish-config"] }),
  });
}

export function usePublishGithub(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: PublishGitHubInput) => publishGithub(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["publications", id] });
      qc.invalidateQueries({ queryKey: ["content", id] });
    },
  });
}

export function useRefreshPublication(contentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (publicationId: string) => refreshPublication(contentId, publicationId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["publications", contentId] });
      qc.invalidateQueries({ queryKey: ["content", contentId] });
      qc.invalidateQueries({ queryKey: ["content"] });
    },
  });
}
