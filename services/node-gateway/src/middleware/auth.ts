import type { FastifyReply, FastifyRequest } from 'fastify';
import { jwtVerify } from 'jose';
import type { Config } from '../config.js';

export interface AuthContext {
  userId: string;
  tenantId: string;
}

export function makeAuthMiddleware(cfg: Config) {
  const key = new TextEncoder().encode(cfg.jwtSecret);

  return async function auth(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const header = request.headers.authorization ?? '';
    if (!header.startsWith('Bearer ')) {
      reply.code(401).send({ error: 'missing bearer token' });
      return;
    }
    const token = header.slice(7);
    try {
      const { payload } = await jwtVerify(token, key, { algorithms: [cfg.jwtAlgorithm] });
      if (payload.kind !== 'access') throw new Error('not an access token');
      (request as FastifyRequest & { auth: AuthContext }).auth = {
        userId: String(payload.sub ?? ''),
        tenantId: String(payload.tid ?? ''),
      };
    } catch {
      reply.code(401).send({ error: 'invalid token' });
      return;
    }
  };
}
