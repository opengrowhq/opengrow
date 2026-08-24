import { apiGet, apiSend } from "@/lib/http";

export type PlaybookKind = "ARTICLE_OUTLINE" | "ARTICLE_DRAFT" | "GENERIC_COPY";

export type Playbook = {
  id: string;
  kind: PlaybookKind;
  name: string;
  version: number;
  system_template: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export const listPlaybooks = (kind?: PlaybookKind) =>
  apiGet<Playbook[]>(kind ? `/playbooks?kind=${kind}` : "/playbooks");

export const createPlaybook = (input: {
  kind: PlaybookKind;
  name: string;
  system_template: string;
}) => apiSend<Playbook>("/playbooks", "POST", input);

export const activatePlaybook = (playbookId: string) =>
  apiSend<Playbook>(`/playbooks/${playbookId}/activate`, "POST");
