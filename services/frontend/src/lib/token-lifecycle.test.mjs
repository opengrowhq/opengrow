import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  REFRESH_SKEW_SECONDS,
  isAuthEndpoint,
  parseJwtExp,
  shouldRefresh,
} from "./token-lifecycle.mjs";

const NOW = 1_800_000_000;

function jwt(payload) {
  const b64 = (obj) => Buffer.from(JSON.stringify(obj)).toString("base64url");
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64(payload)}.fakesig`;
}

describe("parseJwtExp", () => {
  it("reads the exp claim from a JWT", () => {
    assert.equal(parseJwtExp(jwt({ exp: NOW + 300 })), NOW + 300);
  });

  it("returns null for malformed tokens instead of crashing", () => {
    assert.equal(parseJwtExp(null), null);
    assert.equal(parseJwtExp(undefined), null);
    assert.equal(parseJwtExp(""), null);
    assert.equal(parseJwtExp("not-a-jwt"), null);
    assert.equal(parseJwtExp("only.two"), null);
    assert.equal(parseJwtExp("a.b.c"), null); // payload is not valid base64url JSON
    assert.equal(parseJwtExp(jwt({ sub: "user-1" })), null); // no exp claim
    assert.equal(parseJwtExp(jwt({ exp: "soon" })), null); // non-numeric exp
  });

  it("handles base64url padding omissions", () => {
    const token = jwt({ exp: 123 });
    const [h, p, s] = token.split(".");
    assert.equal(parseJwtExp([h, p.replace(/=*$/, ""), s].join(".")), 123);
  });
});

describe("shouldRefresh", () => {
  const refresh = "refresh-token";

  it("is false without an access token or refresh token", () => {
    assert.equal(shouldRefresh(null, refresh, NOW), false);
    assert.equal(shouldRefresh(jwt({ exp: NOW + 10 }), null, NOW), false);
    assert.equal(shouldRefresh(jwt({ exp: NOW + 10 }), "", NOW), false);
  });

  it("is false when the token has plenty of life left", () => {
    assert.equal(shouldRefresh(jwt({ exp: NOW + 3600 }), refresh, NOW), false);
  });

  it("is true when exp is closer than the skew", () => {
    assert.equal(shouldRefresh(jwt({ exp: NOW + REFRESH_SKEW_SECONDS - 1 }), refresh, NOW), true);
    assert.equal(shouldRefresh(jwt({ exp: NOW + 1 }), refresh, NOW), true);
  });

  it("is false exactly at the skew boundary", () => {
    assert.equal(shouldRefresh(jwt({ exp: NOW + REFRESH_SKEW_SECONDS }), refresh, NOW), false);
  });

  it("is true when the token already expired", () => {
    assert.equal(shouldRefresh(jwt({ exp: NOW - 5 }), refresh, NOW), true);
  });

  it("is false for malformed tokens — the 401 retry path handles those", () => {
    assert.equal(shouldRefresh("garbage", refresh, NOW), false);
  });

  it("honours a custom skew", () => {
    const token = jwt({ exp: NOW + 500 });
    assert.equal(shouldRefresh(token, refresh, NOW, 60), false);
    assert.equal(shouldRefresh(token, refresh, NOW, 600), true);
  });
});

describe("isAuthEndpoint", () => {
  it("matches the credential endpoints exactly", () => {
    assert.equal(isAuthEndpoint("/auth/login"), true);
    assert.equal(isAuthEndpoint("/auth/refresh"), true);
    assert.equal(isAuthEndpoint("/auth/refresh?next=%2F"), true);
    assert.equal(isAuthEndpoint("http://api.example.com/auth/login"), true);
  });

  it("does not match other API paths", () => {
    assert.equal(isAuthEndpoint("/auth/me"), false);
    assert.equal(isAuthEndpoint("/auth/logout"), false);
    assert.equal(isAuthEndpoint("/auth/login/"), false);
    assert.equal(isAuthEndpoint("/auth/refreshToken"), false);
    assert.equal(isAuthEndpoint("/billing/subscribe"), false);
    assert.equal(isAuthEndpoint(""), false);
    assert.equal(isAuthEndpoint(null), false);
    assert.equal(isAuthEndpoint("/content/items?page=2"), false);
  });
});
