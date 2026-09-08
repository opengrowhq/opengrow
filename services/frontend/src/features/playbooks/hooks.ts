"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { hasSession } from "@/lib/auth";
import { activatePlaybook, createPlaybook, listPlaybooks, type PlaybookKind } from "./api";

const hasToken = () => hasSession();

export function usePlaybooks(kind?: PlaybookKind) {
  return useQuery({
    queryKey: ["playbooks", kind ?? "all"],
    queryFn: () => listPlaybooks(kind),
    enabled: hasToken(),
  });
}

export function useCreatePlaybook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { kind: PlaybookKind; name: string; system_template: string }) =>
      createPlaybook(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["playbooks"] }),
  });
}

export function useActivatePlaybook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (playbookId: string) => activatePlaybook(playbookId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["playbooks"] }),
  });
}
