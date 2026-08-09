import type { FastifyInstance } from 'fastify';
import type { Config } from '../config.js';

export function registerHealthRoutes(app: FastifyInstance, cfg: Config): void {
  app.get('/health', async () => ({ status: 'ok', service: cfg.serviceName }));

  app.get('/ready', async () => {
    try {
      const r = await fetch(`${cfg.fastapiUrl}/ready`);
      const upstream = (await r.json()) as { ready?: boolean };
      return { ready: r.ok && upstream.ready === true, upstream };
    } catch (e) {
      return { ready: false, error: (e as Error).message };
    }
  });
}
