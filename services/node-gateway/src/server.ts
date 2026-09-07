import Fastify from 'fastify';
import cors from '@fastify/cors';
import rateLimit from '@fastify/rate-limit';
import proxy from '@fastify/http-proxy';
import { loadConfig } from './config.js';
import { registerHealthRoutes } from './routes/health.js';
import { makeAuthMiddleware } from './middleware/auth.js';
import { isPublicPath, pathnameOf } from './public-paths.js';

// API namespaces proxied 1:1 to fastapi-core (same paths the frontend/lite use).
const PROXIED_PREFIXES = [
  '/auth',
  '/assets',
  '/generations',
  '/content',
  '/brands',
  '/analytics',
];

async function main(): Promise<void> {
  const cfg = await loadConfig();
  const app = Fastify({
    logger: { level: cfg.env === 'production' ? 'info' : 'debug' },
    bodyLimit: 26 * 1024 * 1024, // 26 MiB — slightly above FastAPI's 25 MiB
  });

  await app.register(cors, { origin: true, credentials: true });

  // Per-IP rate limit on every route (incl. the authenticated proxy), so the
  // edge auth check can't be brute-forced. Generous default; tune via env.
  await app.register(rateLimit, {
    max: Number(process.env.GATEWAY_RATE_LIMIT_MAX ?? 600),
    timeWindow: '1 minute',
  });

  registerHealthRoutes(app, cfg);

  // Edge JWT check for every proxied request except the public allowlist.
  const auth = makeAuthMiddleware(cfg);
  app.addHook('onRequest', async (request, reply) => {
    if (request.method === 'OPTIONS') return;
    const pathname = pathnameOf(request.url);
    if (isPublicPath(pathname)) return;
    const proxied = PROXIED_PREFIXES.some(
      (p) => pathname === p || pathname.startsWith(`${p}/`),
    );
    if (!proxied) return; // non-proxied (e.g. local /health, /ready) — normal routing
    await auth(request, reply); // sends 401 and short-circuits on failure
  });

  // Proxy each namespace to fastapi-core (auth already enforced by the hook).
  for (const prefix of PROXIED_PREFIXES) {
    await app.register(proxy, {
      upstream: cfg.fastapiUrl,
      prefix,
      rewritePrefix: prefix,
    });
  }

  const port = cfg.port;
  await app.listen({ port, host: '0.0.0.0' });
  app.log.info(`node-gateway listening on ${port}, upstream=${cfg.fastapiUrl}`);
}

main().catch((e) => {
  console.error('node-gateway boot failed', e);
  process.exit(1);
});
