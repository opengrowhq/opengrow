// Pure derivations for the GitHub connection settings card.

/**
 * @typedef {"disconnected" | "instance" | "workspace"} GitHubConnectionState
 * @typedef {{ state: GitHubConnectionState, label: string, tone: "neutral" | "success" | "info" }} GitHubConnectionStatus
 */

/**
 * Display state for a GitHub publish config:
 *  - "workspace": a tenant-stored PAT is in use (source "tenant")
 *  - "instance": publishing works via the instance-level GITHUB_TOKEN (source "env")
 *  - "disconnected": no token anywhere
 * @param {{ configured?: boolean, source?: string | null } | null | undefined} config
 * @returns {GitHubConnectionState}
 */
export function githubConnectionState(config) {
  if (config?.configured && config.source === "tenant") return "workspace";
  if (config?.configured && config.source === "env") return "instance";
  return "disconnected";
}

const STATE_META = {
  workspace: { label: "Workspace token", tone: "success" },
  instance: { label: "Instance token", tone: "info" },
  disconnected: { label: "Not connected", tone: "neutral" },
};

/**
 * @param {{ configured?: boolean, source?: string | null } | null | undefined} config
 * @returns {GitHubConnectionStatus}
 */
export function githubConnectionStatus(config) {
  const state = githubConnectionState(config);
  return { state, ...STATE_META[state] };
}

/** Renders a stored token's last-4 as a masked hint, e.g. "••••1234". */
export function maskedToken(last4) {
  const tail = typeof last4 === "string" ? last4.trim() : "";
  return tail ? `••••${tail}` : "";
}

/**
 * @typedef {{ ok: true, body: { token: string, display_name?: string } }} CredentialInputOk
 * @typedef {{ ok: false, error: string }} CredentialInputErr
 */

/**
 * Trims and validates the paste-PAT form.
 * @param {{ token?: string, display_name?: string } | null | undefined} form
 * @returns {CredentialInputOk | CredentialInputErr}
 */
export function cleanGitHubCredentialInput(form) {
  const token = (form?.token ?? "").trim();
  if (!token) return { ok: false, error: "Paste a personal access token first." };
  const body = { token };
  const displayName = (form?.display_name ?? "").trim();
  if (displayName) body.display_name = displayName;
  return { ok: true, body };
}
