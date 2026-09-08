import Fastify, { type FastifyInstance } from "fastify";
import cors from "@fastify/cors";
import rateLimit from "@fastify/rate-limit";
import proxy from "@fastify/http-proxy";
import type { Config } from "./config.js";
import { registerHealthRoutes } from "./routes/health.js";
import { registerAuthRoutes } from "./routes/auth.js";
import { makeAuthMiddleware } from "./middleware/auth.js";
import { isPublicPath, pathnameOf, PROXIED_PREFIXES } from "./public-paths.js";
import {
  applyCookieAuth,
  maybeRewriteAuthResponse,
  readCookieValue,
  REFRESH_COOKIE,
  shouldIntercept,
} from "./cookies.js";

// API namespaces proxied 1:1 to fastapi-core (same paths the frontend/lite use).

export async function buildApp(cfg: Config): Promise<FastifyInstance> {
  const app = Fastify({
    logger: { level: cfg.env === "production" ? "info" : "debug" },
    bodyLimit: 26 * 1024 * 1024, // 26 MiB — slightly above FastAPI's 25 MiB
    // Caddy terminates TLS; without this request.protocol is always 'http'
    // and auto-detected Secure cookies would never be set.
    trustProxy: true,
  });

  await app.register(cors, {
    origin: true,
    credentials: true,
    // The frontend must be able to READ the mode header (fetch exposes only
    // simple + explicitly exposed headers) and the pagination total.
    exposedHeaders: ["x-og-auth", "X-Total-Count"],
  });

  // Per-IP rate limit on every route (incl. the authenticated proxy), so the
  // edge auth check can't be brute-forced. Generous default; tune via env.
  await app.register(rateLimit, {
    max: Number(process.env.GATEWAY_RATE_LIMIT_MAX ?? 600),
    timeWindow: "1 minute",
  });

  registerHealthRoutes(app, cfg);
  registerAuthRoutes(app, cfg);

  // Cookie → Bearer injection. MUST stay registered before the edge-auth hook
  // below: onRequest hooks run in registration order, and the edge check only
  // looks at the Authorization header.
  app.addHook("onRequest", async (request) => {
    if (request.method === "OPTIONS") return;
    applyCookieAuth(request);
  });

  // Edge JWT check for every proxied request except the public allowlist.
  const auth = makeAuthMiddleware(cfg);
  app.addHook("onRequest", async (request, reply) => {
    if (request.method === "OPTIONS") return;
    const pathname = pathnameOf(request.url);
    if (isPublicPath(pathname)) return;
    const proxied = PROXIED_PREFIXES.some(
      (p) => pathname === p || pathname.startsWith(`${p}/`),
    );
    if (!proxied) return; // non-proxied (e.g. local /health, /ready) — normal routing
    await auth(request, reply); // sends 401 and short-circuits on failure
  });

  // Token-pair → cookie rewrite on token-issuing responses. The pure decision
  // logic lives in maybeRewriteAuthResponse (unit-tested); this adapter only
  // touches Fastify. Never throws — any failure passes the payload through.
  app.addHook("onSend", async (request, reply, payload) => {
    const pathname = pathnameOf(request.url);
    const applyResult = (
      result: ReturnType<typeof maybeRewriteAuthResponse>,
      fallback: unknown,
    ) => {
      if (!result) return fallback;
      if (result.modeHeader) reply.header("x-og-auth", "cookie");
      if (result.setCookies.length > 0) {
        const existing = reply.getHeader("set-cookie");
        const list = Array.isArray(existing)
          ? existing
          : existing
            ? [existing as string]
            : [];
        reply.header("set-cookie", [...list, ...result.setCookies]);
      }
      // The upstream content-length no longer matches the stripped body —
      // drop it so Fastify re-computes it.
      reply.removeHeader("content-length");
      return result.payload;
    };
    try {
      if (!shouldIntercept(pathname, request.method)) return payload;
      const base = {
        pathname,
        method: request.method,
        statusCode: reply.statusCode,
        contentType: reply.getHeader("content-type") as string | undefined,
        secure: cfg.cookieSecure ?? request.protocol === "https",
      };
      if (typeof payload === "string" || Buffer.isBuffer(payload)) {
        return applyResult(
          maybeRewriteAuthResponse({ ...base, payload }),
          payload,
        );
      }
      // Proxied responses arrive as streams (reply.from). Buffer only the
      // small token-issuing JSON endpoints — everything else streams through.
      if (
        payload &&
        typeof (payload as { pipe?: unknown }).pipe === "function"
      ) {
        const buf = await bufferStream(
          payload as import("node:stream").Readable,
        );
        return applyResult(
          maybeRewriteAuthResponse({ ...base, payload: buf }),
          buf,
        );
      }
      return payload;
    } catch {
      return payload;
    }
  });

  // Proxy each namespace to fastapi-core (auth already enforced by the hook).
  for (const prefix of PROXIED_PREFIXES) {
    await app.register(proxy, {
      upstream: cfg.fastapiUrl,
      prefix,
      rewritePrefix: prefix,
      ...(prefix === "/auth"
        ? {
            // Feed /auth/refresh the refresh token from the og_rt cookie: the
            // browser cannot read the httpOnly cookie to place it in the JSON
            // body itself. http-proxy's pass-through parser exposes the body
            // as a stream; we buffer it (refresh payloads are tiny), inject,
            // and hand reply-from a plain object it re-serializes as JSON.
            preHandler: async (request) => {
              if (request.method !== "POST") return;
              if (pathnameOf(request.url) !== "/auth/refresh") return;
              try {
                const existing = request.body;
                if (
                  existing !== null &&
                  typeof existing === "object" &&
                  typeof (existing as { pipe?: unknown }).pipe !== "function" &&
                  typeof (existing as Record<string, unknown>).refresh_token ===
                    "string"
                ) {
                  return; // client already sent one (never override)
                }
                const refreshToken = readCookieValue(
                  request.headers.cookie,
                  REFRESH_COOKIE,
                );
                if (!refreshToken) return;
                let parsed: Record<string, unknown> = {};
                if (
                  existing !== undefined &&
                  existing !== null &&
                  existing !== ""
                ) {
                  if (
                    typeof (existing as { pipe?: unknown }).pipe === "function"
                  ) {
                    const raw = await bufferStream(
                      existing as import("node:stream").Readable,
                    );
                    if (raw.length > 0) {
                      const asJson: unknown = JSON.parse(raw.toString("utf8"));
                      if (
                        asJson !== null &&
                        typeof asJson === "object" &&
                        !Array.isArray(asJson)
                      ) {
                        parsed = asJson as Record<string, unknown>;
                      }
                    }
                  } else if (typeof existing === "object") {
                    parsed = { ...(existing as Record<string, unknown>) };
                  }
                }
                parsed.refresh_token = refreshToken;
                // reply-from only JSON-encodes a replaced body when the request
                // content-type is JSON — make sure it is, or it would try to
                // measure an object with Buffer.byteLength and 500.
                const ct = request.headers["content-type"] ?? "";
                if (
                  typeof ct !== "string" ||
                  !ct.includes("application/json")
                ) {
                  request.headers["content-type"] = "application/json";
                }
                request.body = parsed;
              } catch {
                // Unparseable body: pass the request through untouched — core
                // will reject it, same as a malformed direct call.
              }
            },
          }
        : {}),
    });
  }

  return app;
}

function bufferStream(stream: import("node:stream").Readable): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    stream.on("data", (chunk: Buffer) => chunks.push(chunk));
    stream.on("end", () => resolve(Buffer.concat(chunks)));
    stream.on("error", reject);
  });
}
