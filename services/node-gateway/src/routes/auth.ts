import type { FastifyInstance, FastifyRequest } from "fastify";
import type { Config } from "../config.js";
import {
  buildSessionCookies,
  REFRESH_COOKIE,
  SESSION_COOKIE,
} from "../cookies.js";

// Resolve the Secure flag: pinned via COOKIE_SECURE, else per-request protocol.
function secureFor(cfg: Config, request: FastifyRequest): boolean {
  return cfg.cookieSecure ?? request.protocol === "https";
}

/**
 * Local (non-proxied) auth-session routes. Both live under the proxied /auth
 * prefix — Fastify's router prefers these static routes over the proxy's
 * wildcard, so they shadow the upstream for these two paths only.
 */
export function registerAuthRoutes(app: FastifyInstance, cfg: Config): void {
  // Sign out: expire both cookies. Best-effort by design — a missing cookie is
  // already the goal state.
  app.post("/auth/logout", async (request, reply) => {
    const secure = secureFor(cfg, request) ? "; Secure" : "";
    reply.header("set-cookie", [
      `${SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0${secure}`,
      `${REFRESH_COOKIE}=; Path=/auth; HttpOnly; SameSite=Strict; Max-Age=0${secure}`,
    ]);
    return reply.code(204).send();
  });

  // One-shot handoff for tokens that arrive in a URL fragment (OAuth callback:
  // /login#access_token=...&refresh_token=...). The frontend POSTs them here
  // ONCE so they move straight into httpOnly cookies without ever touching
  // JS-accessible storage.
  //
  // Tokens are NOT validated here — that is deliberate: the edge JWT check
  // validates the access token on the very next proxied request, so a forged
  // /auth/session buys nothing beyond a cookie the edge will reject (same
  // exposure as presenting a bad Bearer header directly). The strict checks
  // below exist to stop session fixation and simple cross-site form posts:
  // - X-Requested-With: XMLHttpRequest is required, which a cross-site
  //   <form>/navigator.sendBeacon('simple') cannot set (non-simple header);
  //   together with SameSite=Strict cookies this blocks CSRF-style fixation.
  // - Rate limit 30/min/IP slows brute stuffing of someone else's session.
  app.post(
    "/auth/session",
    {
      config: { rateLimit: { max: 30, timeWindow: "1 minute" } },
    },
    async (request, reply) => {
      if (request.headers["x-requested-with"] !== "XMLHttpRequest") {
        return reply
          .code(403)
          .send({ error: "missing X-Requested-With header" });
      }
      const body = request.body;
      const valid =
        typeof body === "object" &&
        body !== null &&
        typeof (body as Record<string, unknown>).access_token === "string" &&
        (body as Record<string, unknown>).access_token !== "" &&
        ((body as Record<string, unknown>).refresh_token === undefined ||
          typeof (body as Record<string, unknown>).refresh_token === "string");
      if (!valid) {
        return reply
          .code(400)
          .send({ error: "body must be { access_token, refresh_token? }" });
      }
      const pair = body as { access_token: string; refresh_token?: string };
      reply.header(
        "set-cookie",
        buildSessionCookies(pair, { secure: secureFor(cfg, request) }),
      );
      reply.header("x-og-auth", "cookie");
      return reply.code(204).send();
    },
  );
}
