"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { loadToken } from "@/lib/auth";
import {
  approveOrchestratorOutline,
  createOrchestratorRun,
  getOrchestratorRun,
  listOrchestratorRuns,
  resumeOrchestratorRun,
  type OrchestratorRun,
} from "./orchestrator-api";

// States the worker drives forward — user-driven pauses (AWAITING_*) don't
// need polling; they change only when the user acts.
const ACTIVE = ["QUEUED", "GENERATING", "PROMOTING"];
// States where a run detail should stop polling (worker finished OR waiting
// on the user).
const STALLED = ["COMPLETE", "FAILED", "AWAITING_OUTLINE_APPROVAL"];

const hasActiveRun = (runs: OrchestratorRun[] | undefined) =>
  (runs ?? []).some((r) => ACTIVE.includes(r.status));

export function useOrchestratorRuns() {
  return useQuery({
    queryKey: ["orchestrator", "runs"],
    queryFn: listOrchestratorRuns,
    enabled: !!loadToken(),
    refetchInterval: (q) =>
      hasActiveRun(q.state.data as OrchestratorRun[] | undefined) ? 3000 : false,
  });
}

export function useOrchestratorRun(id: string | null) {
  return useQuery({
    queryKey: ["orchestrator", "runs", id],
    queryFn: () => getOrchestratorRun(id as string),
    enabled: !!id && !!loadToken(),
    refetchInterval: (q) => {
      const s = (q.state.data as OrchestratorRun | undefined)?.status;
      return s && STALLED.includes(s) ? false : 2000;
    },
  });
}

function useInvalidatingMutation<TVars, TData>(
  fn: (vars: TVars) => Promise<TData>,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orchestrator"] }),
  });
}

export function useCreateOrchestratorRun() {
  return useInvalidatingMutation(createOrchestratorRun);
}

export function useApproveOrchestratorOutline() {
  return useInvalidatingMutation(
    ({ id, outline }: { id: string; outline: { heading: string; points: string[] }[] }) =>
      approveOrchestratorOutline(id, outline),
  );
}

export function useResumeOrchestratorRun() {
  return useInvalidatingMutation((id: string) => resumeOrchestratorRun(id));
}
