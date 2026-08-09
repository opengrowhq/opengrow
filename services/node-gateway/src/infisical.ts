interface InfisicalOptions {
  url: string;
  projectId: string;
  environment: string;
  token: string;
}

/**
 * Minimal Infisical client — pulls secrets via REST at boot.
 * No SDK dep to keep the image small.
 */
export async function fetchInfisicalSecrets(opts: InfisicalOptions): Promise<Record<string, string>> {
  if (!opts.token) return {};
  const url = `${opts.url}/api/v3/secrets/raw?workspaceId=${opts.projectId}&environment=${opts.environment}`;
  try {
    const resp = await fetch(url, {
      headers: { Authorization: `Bearer ${opts.token}` },
    });
    if (!resp.ok) return {};
    const data = (await resp.json()) as { secrets?: { secretKey: string; secretValue: string }[] };
    const out: Record<string, string> = {};
    for (const s of data.secrets ?? []) {
      out[s.secretKey] = s.secretValue;
    }
    return out;
  } catch {
    return {};
  }
}
