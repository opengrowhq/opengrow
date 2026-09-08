import { test } from "node:test";
import assert from "node:assert/strict";
import {
  applyCookieAuth,
  buildSessionCookies,
  maybeRewriteAuthResponse,
  readCookieValue,
  REFRESH_COOKIE,
  SESSION_COOKIE,
  shouldIntercept,
  stripTokenPair,
} from "./cookies.js";

// decodeJwt only parses (no verify), so a signed-looking but unsigned token is fine.
function makeJwt(payload: object): string {
  const b64 = (o: object) =>
    Buffer.from(JSON.stringify(o)).toString("base64url");
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64(payload)}.fakesig`;
}

const NOW = 1_700_000_000;

// ------------------------------ shouldIntercept ------------------------------

test("shouldIntercept matches token-issuing POSTs only", () => {
  const yes = [
    ["/auth/login", "POST"],
    ["/auth/refresh", "POST"],
    ["/auth/set-password", "POST"],
    ["/invites/abc123/accept", "POST"],
  ] as const;
  for (const [p, m] of yes)
    assert.equal(shouldIntercept(p, m), true, `${m} ${p}`);

  const no = [
    ["/auth/login", "GET"],
    ["/auth/refresh", "GET"],
    ["/auth/set-password", "PUT"],
    ["/invites/abc123/accept", "GET"],
    ["/invites/abc123", "POST"],
    ["/invites/abc123/revoke", "POST"],
    ["/auth/me", "POST"],
    ["/auth/logout", "POST"],
    ["/auth/session", "POST"],
    ["/content", "POST"],
  ] as const;
  for (const [p, m] of no)
    assert.equal(shouldIntercept(p, m), false, `${m} ${p}`);
});

// ---------------------------- buildSessionCookies ----------------------------

test("buildSessionCookies derives maxAge from JWT exp claims", () => {
  const access = makeJwt({ sub: "u1", exp: NOW + 3600 });
  const refresh = makeJwt({ sub: "u1", kind: "refresh", exp: NOW + 86400 });
  const cookies = buildSessionCookies(
    { access_token: access, refresh_token: refresh },
    { secure: true, nowSec: NOW },
  );
  assert.equal(cookies.length, 2);
  assert.equal(
    cookies[0],
    `${SESSION_COOKIE}=${access}; Path=/; HttpOnly; SameSite=Strict; Max-Age=3600; Secure`,
  );
  assert.equal(
    cookies[1],
    `${REFRESH_COOKIE}=${refresh}; Path=/auth; HttpOnly; SameSite=Strict; Max-Age=86400; Secure`,
  );
});

test("buildSessionCookies omits Secure and refresh cookie per options", () => {
  const access = makeJwt({ exp: NOW + 60 });
  const cookies = buildSessionCookies(
    { access_token: access },
    { secure: false, nowSec: NOW },
  );
  assert.equal(cookies.length, 1);
  assert.ok(!cookies[0].includes("Secure"));
  assert.ok(cookies[0].includes("Max-Age=60"));
});

test("buildSessionCookies drops maxAge for malformed or exp-less tokens", () => {
  const noExp = makeJwt({ sub: "u1" });
  const malformed = "not-a-jwt";
  const cookies = buildSessionCookies(
    { access_token: noExp, refresh_token: malformed },
    { secure: false, nowSec: NOW },
  );
  assert.equal(cookies.length, 2);
  assert.ok(!cookies[0].includes("Max-Age"));
  assert.ok(!cookies[1].includes("Max-Age"));
});

test("buildSessionCookies refuses cookie-unsafe token values", () => {
  const evil = "abc; Path=/\r\nX-Injected: 1";
  const cookies = buildSessionCookies(
    { access_token: evil, refresh_token: evil },
    { secure: true },
  );
  assert.deepEqual(cookies, []);
});

test("buildSessionCookies clamps negative exp to Max-Age=0", () => {
  const expired = makeJwt({ exp: NOW - 10 });
  const cookies = buildSessionCookies(
    { access_token: expired },
    { secure: false, nowSec: NOW },
  );
  assert.ok(cookies[0].includes("Max-Age=0"));
});

// ------------------------------- stripTokenPair ------------------------------

test("stripTokenPair removes tokens from a pair-shaped body", () => {
  const body = { access_token: "a", refresh_token: "r", token_type: "bearer" };
  const { stripped, hadTokens } = stripTokenPair(body);
  assert.equal(hadTokens, true);
  assert.deepEqual(stripped, { token_type: "bearer" });
  assert.deepEqual(body, {
    access_token: "a",
    refresh_token: "r",
    token_type: "bearer",
  }); // no mutation
});

test("stripTokenPair leaves non-pair bodies unchanged", () => {
  for (const body of [
    null,
    undefined,
    "x",
    42,
    [1, 2],
    {},
    { access_token: 7 },
    { token: "a" },
  ]) {
    const { stripped, hadTokens } = stripTokenPair(body);
    assert.equal(hadTokens, false);
    assert.equal(stripped, body);
  }
});

// ------------------------------- readCookieValue -----------------------------

test("readCookieValue parses the raw cookie header", () => {
  const h = `other=1; ${SESSION_COOKIE}=tok123; ${REFRESH_COOKIE}=rt%3D456`;
  assert.equal(readCookieValue(h, SESSION_COOKIE), "tok123");
  assert.equal(readCookieValue(h, REFRESH_COOKIE), "rt=456");
  assert.equal(readCookieValue(h, "missing"), null);
  assert.equal(readCookieValue(undefined, SESSION_COOKIE), null);
  assert.equal(
    readCookieValue("og_at=100%malformed", SESSION_COOKIE),
    "100%malformed",
  ); // no throw
});

// ------------------------------- applyCookieAuth -----------------------------

test("applyCookieAuth injects Bearer from the session cookie", () => {
  const req: { headers: Record<string, unknown> } = {
    headers: { cookie: `${SESSION_COOKIE}=tok` },
  };
  assert.equal(applyCookieAuth(req), true);
  assert.equal(req.headers.authorization, "Bearer tok");
});

test("applyCookieAuth never overrides an existing Authorization header", () => {
  const req: { headers: Record<string, unknown> } = {
    headers: { cookie: `${SESSION_COOKIE}=tok`, authorization: "Bearer other" },
  };
  assert.equal(applyCookieAuth(req), false);
  assert.equal(req.headers.authorization, "Bearer other");
});

test("applyCookieAuth is a no-op without the cookie", () => {
  const req: { headers: Record<string, unknown> } = { headers: {} };
  assert.equal(applyCookieAuth(req), false);
  assert.equal("authorization" in req.headers, false);
});

// --------------------------- maybeRewriteAuthResponse ------------------------

test("maybeRewriteAuthResponse rewrites a login token pair into cookies", () => {
  const access = makeJwt({ exp: NOW + 900 });
  const refresh = makeJwt({ exp: NOW + 1800 });
  const body = JSON.stringify({
    access_token: access,
    refresh_token: refresh,
    token_type: "bearer",
  });
  const result = maybeRewriteAuthResponse({
    pathname: "/auth/login",
    method: "POST",
    statusCode: 200,
    contentType: "application/json",
    payload: body,
    secure: true,
    nowSec: NOW,
  });
  assert.ok(result);
  assert.equal(result.modeHeader, true);
  assert.equal(result.setCookies.length, 2);
  assert.ok(result.setCookies[0].startsWith(`${SESSION_COOKIE}=${access}`));
  assert.deepEqual(JSON.parse(result.payload), { token_type: "bearer" });
});

test("maybeRewriteAuthResponse accepts Buffer payloads and invite accepts", () => {
  const access = makeJwt({ exp: NOW + 900 });
  const result = maybeRewriteAuthResponse({
    pathname: "/invites/tok/accept",
    method: "POST",
    statusCode: 200,
    contentType: "application/json; charset=utf-8",
    payload: Buffer.from(
      JSON.stringify({ access_token: access, refresh_token: null, id: "u" }),
    ),
    secure: false,
    nowSec: NOW,
  });
  assert.ok(result);
  assert.equal(result.setCookies.length, 1); // null refresh_token → no og_rt
  assert.deepEqual(JSON.parse(result.payload), { id: "u" });
});

test("maybeRewriteAuthResponse passes through everything else", () => {
  const access = makeJwt({ exp: NOW + 900 });
  const cases = [
    {
      pathname: "/auth/me",
      method: "POST",
      statusCode: 200,
      contentType: "application/json",
    },
    {
      pathname: "/auth/login",
      method: "GET",
      statusCode: 200,
      contentType: "application/json",
    },
    {
      pathname: "/auth/login",
      method: "POST",
      statusCode: 401,
      contentType: "application/json",
    },
    {
      pathname: "/auth/login",
      method: "POST",
      statusCode: 200,
      contentType: "text/html",
    },
    {
      pathname: "/auth/login",
      method: "POST",
      statusCode: 204,
      contentType: undefined,
    },
  ] as const;
  for (const c of cases) {
    assert.equal(
      maybeRewriteAuthResponse({
        ...c,
        payload: JSON.stringify({ access_token: access }),
        secure: false,
      }),
      null,
      JSON.stringify(c),
    );
  }
  // malformed JSON body
  assert.equal(
    maybeRewriteAuthResponse({
      pathname: "/auth/login",
      method: "POST",
      statusCode: 200,
      contentType: "application/json",
      payload: "{not json",
      secure: false,
    }),
    null,
  );
  // JSON but no tokens
  assert.equal(
    maybeRewriteAuthResponse({
      pathname: "/auth/login",
      method: "POST",
      statusCode: 200,
      contentType: "application/json",
      payload: '{"detail":"ok"}',
      secure: false,
    }),
    null,
  );
});
