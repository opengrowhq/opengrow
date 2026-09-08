import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import type { FastifyInstance } from "fastify";
import { buildApp } from "./app.js";
import type { Config } from "./config.js";
import { REFRESH_COOKIE, SESSION_COOKIE } from "./cookies.js";

const NOW = 1_700_000_000;

function makeJwt(payload: object): string {
  const b64 = (o: object) =>
    Buffer.from(JSON.stringify(o)).toString("base64url");
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64(payload)}.fakesig`;
}

const cfg: Config = {
  serviceName: "node-gateway",
  env: "test",
  port: 0,
  fastapiUrl: "http://127.0.0.1:9", // unreachable on purpose — local routes only
  jwtSecret: "test-secret",
  jwtAlgorithm: "HS256",
  cookieSecure: false,
};

let app: FastifyInstance;

before(async () => {
  app = await buildApp(cfg);
  await app.ready();
});

after(async () => {
  await app.close();
});

test("POST /auth/logout clears both cookies and returns 204", async () => {
  const res = await app.inject({ method: "POST", url: "/auth/logout" });
  assert.equal(res.statusCode, 204);
  const cookies = res.headers["set-cookie"];
  assert.ok(Array.isArray(cookies));
  assert.equal(cookies.length, 2);
  assert.ok(
    cookies[0].startsWith(
      `${SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0`,
    ),
  );
  assert.ok(
    cookies[1].startsWith(
      `${REFRESH_COOKIE}=; Path=/auth; HttpOnly; SameSite=Strict; Max-Age=0`,
    ),
  );
});

test("POST /auth/session rejects cross-site posts without X-Requested-With", async () => {
  const res = await app.inject({
    method: "POST",
    url: "/auth/session",
    payload: { access_token: makeJwt({ exp: NOW + 3600 }) },
  });
  assert.equal(res.statusCode, 403);
  assert.equal(res.headers["set-cookie"] ?? null, null);
});

test("POST /auth/session rejects invalid bodies", async () => {
  for (const payload of [{}, { access_token: "" }, { access_token: 7 }]) {
    const res = await app.inject({
      method: "POST",
      url: "/auth/session",
      headers: { "x-requested-with": "XMLHttpRequest" },
      payload,
    });
    assert.equal(res.statusCode, 400, JSON.stringify(payload));
  }
  // Non-JSON payloads are rejected too (415 from the content-type parser).
  const res = await app.inject({
    method: "POST",
    url: "/auth/session",
    headers: { "x-requested-with": "XMLHttpRequest" },
    payload: "nope",
  });
  assert.equal(res.statusCode, 415);
});

test("POST /auth/session sets httpOnly cookies and the mode header", async () => {
  const realNow = Math.floor(Date.now() / 1000);
  const access = makeJwt({ exp: realNow + 3600 });
  const refresh = makeJwt({ exp: realNow + 86400 });
  const res = await app.inject({
    method: "POST",
    url: "/auth/session",
    headers: { "x-requested-with": "XMLHttpRequest" },
    payload: { access_token: access, refresh_token: refresh },
  });
  assert.equal(res.statusCode, 204);
  assert.equal(res.headers["x-og-auth"], "cookie");
  const cookies = res.headers["set-cookie"];
  assert.ok(Array.isArray(cookies));
  assert.ok(
    cookies.some(
      (c) =>
        c.startsWith(
          `${SESSION_COOKIE}=${access}; Path=/; HttpOnly; SameSite=Strict; Max-Age=`,
        ) && c.includes("Max-Age=3600"),
    ),
  );
  assert.ok(
    cookies.some(
      (c) =>
        c.startsWith(
          `${REFRESH_COOKIE}=${refresh}; Path=/auth; HttpOnly; SameSite=Strict`,
        ) && c.includes("Max-Age=86400"),
    ),
  );
});

test("POST /auth/session accepts refresh_token omitted", async () => {
  const res = await app.inject({
    method: "POST",
    url: "/auth/session",
    headers: { "x-requested-with": "XMLHttpRequest" },
    payload: { access_token: makeJwt({ exp: NOW + 3600 }) },
  });
  assert.equal(res.statusCode, 204);
  const cookies = res.headers["set-cookie"];
  assert.ok(Array.isArray(cookies));
  assert.equal(cookies.length, 1);
});

test("POST /auth/session is rate limited to 30 per minute per IP", async () => {
  let last = 0;
  for (let i = 0; i < 31; i++) {
    const res = await app.inject({
      method: "POST",
      url: "/auth/session",
      headers: { "x-requested-with": "XMLHttpRequest" },
      payload: { access_token: makeJwt({ exp: NOW + 3600 }) },
    });
    last = res.statusCode;
  }
  assert.equal(last, 429);
});

test("local health routes still respond", async () => {
  const res = await app.inject({ method: "GET", url: "/health" });
  assert.equal(res.statusCode, 200);
});

// Live-upstream integration: exercises the onSend stream rewrite and the
// cookie→Authorization injection through @fastify/http-proxy — paths that
// unit tests over maybeRewriteAuthResponse cannot reach.

async function withFakeUpstream(
  fn: (base: {
    upstream: string;
    access: string;
    refresh: string;
  }) => Promise<void>,
): Promise<void> {
  const now = Math.floor(Date.now() / 1000);
  const access = makeJwt({
    sub: "u1",
    tid: "t1",
    kind: "access",
    exp: now + 3600,
  });
  const refresh = makeJwt({ sub: "u1", kind: "refresh", exp: now + 86400 });
  const upstream = createServer((req, res) => {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", () => {
      res.setHeader("content-type", "application/json");
      if (req.url === "/auth/login") {
        res.end(
          JSON.stringify({
            access_token: access,
            refresh_token: refresh,
            token_type: "bearer",
          }),
        );
      } else if (req.url === "/auth/refresh") {
        res.end(
          JSON.stringify({
            access_token: access,
            refresh_token: refresh,
            got_refresh:
              (JSON.parse(body || "{}") as { refresh_token?: string })
                .refresh_token ?? null,
          }),
        );
      } else if (req.url === "/auth/me") {
        if (typeof req.headers.authorization === "string") {
          res.statusCode = 200;
          res.end(JSON.stringify({ auth: req.headers.authorization }));
        } else {
          res.statusCode = 401;
          res.end(JSON.stringify({ detail: "unauthorized" }));
        }
      } else {
        res.statusCode = 404;
        res.end("{}");
      }
    });
  });
  await new Promise<void>((resolve) =>
    upstream.listen(0, "127.0.0.1", resolve),
  );
  const address = upstream.address();
  if (address === null || typeof address === "string")
    throw new Error("no address");
  try {
    await fn({ upstream: `http://127.0.0.1:${address.port}`, access, refresh });
  } finally {
    await new Promise((resolve) => upstream.close(resolve));
  }
}

test("proxied login is rewritten: tokens stripped from body, set as cookies", async () => {
  await withFakeUpstream(async ({ upstream, access, refresh }) => {
    const testApp = await buildApp({ ...cfg, fastapiUrl: upstream });
    await testApp.ready();
    try {
      const res = await testApp.inject({
        method: "POST",
        url: "/auth/login",
        headers: { "content-type": "application/x-www-form-urlencoded" },
        payload: "username=a%40b.com&password=secret",
      });
      assert.equal(res.statusCode, 200);
      assert.deepEqual(JSON.parse(res.body), { token_type: "bearer" });
      assert.equal(res.headers["x-og-auth"], "cookie");
      const cookies = res.headers["set-cookie"];
      assert.ok(Array.isArray(cookies));
      assert.ok(
        cookies.some((c) =>
          c.startsWith(
            `${SESSION_COOKIE}=${access}; Path=/; HttpOnly; SameSite=Strict`,
          ),
        ),
      );
      assert.ok(
        cookies.some((c) =>
          c.startsWith(
            `${REFRESH_COOKIE}=${refresh}; Path=/auth; HttpOnly; SameSite=Strict`,
          ),
        ),
      );
    } finally {
      await testApp.close();
    }
  });
});

test("og_at cookie is injected as Bearer and passes edge auth; refresh body gets og_rt", async () => {
  await withFakeUpstream(async ({ upstream }) => {
    const testApp = await buildApp({
      ...cfg,
      fastapiUrl: upstream,
      jwtSecret: "test-secret",
    });
    await testApp.ready();
    try {
      // Sign a token the edge verifier accepts (upstream fixtures are unsigned).
      const { SignJWT } = await import("jose");
      const key = new TextEncoder().encode("test-secret");
      const now = Math.floor(Date.now() / 1000);
      const signedAccess = await new SignJWT({ tid: "t1", kind: "access" })
        .setProtectedHeader({ alg: "HS256" })
        .setSubject("u1")
        .setExpirationTime(now + 3600)
        .sign(key);
      const signedRefresh = await new SignJWT({ kind: "refresh" })
        .setProtectedHeader({ alg: "HS256" })
        .setSubject("u1")
        .setExpirationTime(now + 86400)
        .sign(key);

      const session = await testApp.inject({
        method: "POST",
        url: "/auth/session",
        headers: { "x-requested-with": "XMLHttpRequest" },
        payload: { access_token: signedAccess, refresh_token: signedRefresh },
      });
      const cookies = (session.headers["set-cookie"] as string[])
        .map((c) => c.split(";")[0])
        .join("; ");

      const me = await testApp.inject({
        method: "GET",
        url: "/auth/me",
        headers: { cookie: cookies },
      });
      assert.equal(me.statusCode, 200, me.body);
      // The edge received the token from the httpOnly cookie, not from JS.
      assert.equal(JSON.parse(me.body).auth, `Bearer ${signedAccess}`);

      const anon = await testApp.inject({ method: "GET", url: "/auth/me" });
      assert.equal(anon.statusCode, 401);

      const refreshed = await testApp.inject({
        method: "POST",
        url: "/auth/refresh",
        headers: { "content-type": "application/json", cookie: cookies },
        payload: {},
      });
      assert.equal(refreshed.statusCode, 200);
      // The gateway fed fastapi-core the refresh token from the httpOnly
      // cookie, then stripped the rotated pair from the response body.
      assert.deepEqual(JSON.parse(refreshed.body), {
        got_refresh: signedRefresh,
      });
    } finally {
      await testApp.close();
    }
  });
});
