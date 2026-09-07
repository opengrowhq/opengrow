import { fetchInfisicalSecrets } from './infisical.js';

export interface Config {
  serviceName: string;
  env: string;
  port: number;
  fastapiUrl: string;
  jwtSecret: string;
  jwtAlgorithm: 'HS256';
}

export async function loadConfig(): Promise<Config> {
  const secrets = await fetchInfisicalSecrets({
    url: process.env.INFISICAL_URL!,
    projectId: process.env.INFISICAL_PROJECT_ID!,
    environment: process.env.INFISICAL_ENVIRONMENT!,
    token: process.env.INFISICAL_TOKEN!,
  });

  // Fail loudly when Infisical is configured but the JWT secret came back
  // empty — booting with no JWT secret would let the edge auth verify
  // nothing. In lite mode (no Infisical token) this check is skipped; the
  // auth middleware rejects the empty secret on its own path.
  const infisicalConfigured = Boolean(process.env.INFISICAL_TOKEN);
  if (infisicalConfigured && !secrets.JWT_SECRET) {
    throw new Error(
      'Infisical is configured (INFISICAL_TOKEN set) but returned no JWT_SECRET — refusing to boot',
    );
  }

  return {
    serviceName: process.env.SERVICE_NAME ?? 'node-gateway',
    env: process.env.NODE_ENV ?? 'development',
    port: 3001,
    fastapiUrl: process.env.FASTAPI_URL ?? 'http://fastapi-core:8000',
    jwtSecret: secrets.JWT_SECRET ?? '',
    jwtAlgorithm: 'HS256',
  };
}
