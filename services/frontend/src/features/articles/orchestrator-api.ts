import { apiGet, apiSend } from "@/lib/http";

export type OrchestratorRun = {
  run_id: string;
  status: string;
  step: string | null;
  brief: string | null;
  generation_id: string | null;
  content_piece_id: string | null;
  result: string | null;
  error_message: string | null;
  outline: { heading: string; points: string[] }[] | null;
  outline_generation_id: string | null;
  draft_generation_id: string | null;
};

export const createOrchestratorRun = (body: {
  brief: string;
  article: Record<string, unknown>;
  pause_for_outline_approval?: boolean;
  auto_approve?: boolean;
  title?: string;
}) => apiSend<OrchestratorRun>("/orchestrator/runs", "POST", body);

export const listOrchestratorRuns = () => apiGet<OrchestratorRun[]>("/orchestrator/runs");

export const getOrchestratorRun = (id: string) =>
  apiGet<OrchestratorRun>(`/orchestrator/runs/${id}`);

export const approveOrchestratorOutline = (
  id: string,
  outline: { heading: string; points: string[] }[],
) => apiSend<OrchestratorRun>(`/orchestrator/runs/${id}/outline/approve`, "POST", { outline });

export const resumeOrchestratorRun = (id: string) =>
  apiSend<OrchestratorRun>(`/orchestrator/runs/${id}/resume`, "POST", {});
