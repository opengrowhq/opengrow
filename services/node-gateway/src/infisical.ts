interface InfisicalOptions {
  url: string;
  projectId: string;
  environment: string;
  token: string;
}

/** Error thrown when Infisical is configured but unreachable or incomplete. */
export class InfisicalFetchError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'InfisicalFetchError';
  }
}

/**
 * Minimal Infisical client — pulls secrets via REST at boot.
 * No SDK dep to keep the image small.
 *
 * Fail loudly: when a token is configured, any fetch/parse failure or a
 * non-2xx response throws (boot aborts in server.ts) instead of silently
 * returning {} and booting with empty secrets. With no token configured
 * (lite mode) it returns {} unchanged.
 */
export async function fetchInfisicalSecrets(opts: InfisicalOptions): Promise<Record<string, string>> {
  if (!opts.token) return {};
  const url = `${opts.url}/api/v3/secrets/raw?workspaceId=${opts.projectId}&environment=${opts.environment}`;
  let resp: Response;
  try {
    resp = await fetch(url, {
      headers: { Authorization: `Bearer ${opts.token}` },
    });
  } catch (e) {
    throw new InfisicalFetchError(
      `Infisical fetch failed (${opts.url}): ${e instanceof Error ? e.message : String(e)}`,
    );
  }
  if (!resp.ok) {
    throw new InfisicalFetchError(
      `Infisical returned HTTP ${resp.status} for ${opts.url} — refusing to boot with empty secrets`,
    );
  }
  const data = (await resp.json()) as { secrets?: { secretKey: string; secretValue: string }[] };
  const out: Record<string, string> = {};
  for (const s of data.secrets ?? []) {
    out[s.secretKey] = s.secretValue;
  }
  return out;
}
