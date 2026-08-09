import { API_BASE, ApiError, apiDelete, apiGet, apiSend, authHeaders } from "@/lib/http";

export type ContentPiece = {
  id: string;
  title: string;
  body: string;
  format: string | null;
  status: string;
  source_generation_id: string | null;
  next_action: string | null;
  due_at: string | null;
  created_at: string;
  updated_at: string;
};

export type PublicationTarget = {
  repo?: string;
  path?: string;
  branch?: string;
  base_branch?: string;
  pr_number?: number;
  commit_sha?: string;
  state?: string; // "open" | "closed"
  merged?: boolean;
  merged_at?: string | null;
  warnings?: string[] | null;
};

export type Publication = {
  id: string;
  content_piece_id: string;
  channel: string;
  status: string;
  url: string | null;
  external_ref: string | null;
  error_message: string | null;
  target: PublicationTarget | null;
  created_at: string;
};

export type GitHubPublishConfig = {
  configured: boolean;
  api_url: string;
  source: string | null;
  has_tenant_credential: boolean;
  token_last4: string | null;
  display_name?: string | null;
};

export type GitHubCredentialOut = {
  configured: boolean;
  source: string;
  token_last4: string;
  display_name: string | null;
  api_url: string;
};

export type GenerationSummary = {
  id: string;
  status: string;
  brief: string;
  result: string | null;
  error_message: string | null;
  task_id: string | null;
  parent_generation_id: string | null;
};

export type ContentPatch = {
  title?: string;
  body?: string;
  format?: string | null;
  next_action?: string | null;
  due_at?: string | null;
};
export type PublishGitHubInput = {
  repo: string;
  path?: string;
  base_branch?: string;
  branch?: string;
  commit_message?: string;
  pr_title?: string;
  pr_body?: string;
  draft?: boolean;
  labels?: string[];
  reviewers?: string[];
};

export const listContent = () => apiGet<ContentPiece[]>("/content");
export const getContent = (id: string) => apiGet<ContentPiece>(`/content/${id}`);
export const getGeneration = (id: string) =>
  apiGet<GenerationSummary>(`/generations/${id}`);

export const createContent = (body: {
  title: string;
  body?: string;
  format?: string | null;
  next_action?: string | null;
  due_at?: string | null;
}) =>
  apiSend<ContentPiece>("/content", "POST", body);

export const createFromGeneration = (generation_id: string, title?: string) =>
  apiSend<ContentPiece>("/content/from-generation", "POST", { generation_id, title });

export const updateContent = (id: string, patch: ContentPatch) =>
  apiSend<ContentPiece>(`/content/${id}`, "PATCH", patch);

export const transitionContent = (id: string, status: string) =>
  apiSend<ContentPiece>(`/content/${id}/transition`, "POST", { status });

export const publishGithub = (id: string, body: PublishGitHubInput) =>
  apiSend<Publication>(`/content/${id}/publish/github`, "POST", body);

export const listPublications = (id: string) =>
  apiGet<Publication[]>(`/content/${id}/publications`);

export const refreshPublication = (contentId: string, publicationId: string) =>
  apiSend<Publication>(
    `/content/${contentId}/publications/${publicationId}/refresh`,
    "POST",
  );

export const getGitHubPublishConfig = () =>
  apiGet<GitHubPublishConfig>("/content/publish/github/config");

export const upsertGitHubCredential = (body: { token: string; display_name?: string }) =>
  apiSend<GitHubCredentialOut>("/content/publish/github/credentials", "POST", body);

export const deleteGitHubCredential = () =>
  apiDelete("/content/publish/github/credentials");

export async function exportMarkdown(id: string): Promise<string> {
  const res = await fetch(`${API_BASE}/content/${id}/export.md`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new ApiError(res.status, "Export failed");
  return res.text();
}
