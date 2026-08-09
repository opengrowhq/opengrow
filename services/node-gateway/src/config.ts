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

  return {
    serviceName: process.env.SERVICE_NAME ?? 'node-gateway',
    env: process.env.NODE_ENV ?? 'development',
    port: 3001,
    fastapiUrl: process.env.FASTAPI_URL ?? 'http://fastapi-core:8000',
    jwtSecret: secrets.JWT_SECRET ?? '',
    jwtAlgorithm: 'HS256',
  };
}
