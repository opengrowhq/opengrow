import { test } from "node:test";
import assert from "node:assert/strict";
import { isPublicPath, pathnameOf, PROXIED_PREFIXES } from "./public-paths.js";

// Every API namespace the frontend calls (services/frontend/src/features/*/api.ts)
// must be proxied to fastapi-core, otherwise the gateway 404s those calls.
const FRONTEND_API_PREFIXES = [
  "/auth",
  "/assets",
  "/generations",
  "/content",
  "/brands",
  "/analytics",
  "/invites",
  "/playbooks",
  "/orchestrator",
];

test("every frontend API prefix is proxied to fastapi-core", () => {
  for (const prefix of FRONTEND_API_PREFIXES) {
    assert.ok(
      PROXIED_PREFIXES.includes(prefix),
      `missing proxied prefix: ${prefix}`,
    );
  }
});

test("login, tracking, and health are public", () => {
  assert.equal(isPublicPath("/auth/login"), true);
  assert.equal(isPublicPath("/auth/refresh"), true);
  assert.equal(isPublicPath("/auth/logout"), true);
  assert.equal(isPublicPath("/auth/session"), true);
  assert.equal(isPublicPath("/analytics/pixel.gif"), true);
  assert.equal(isPublicPath("/analytics/track"), true);
  assert.equal(isPublicPath("/health"), true);
  assert.equal(isPublicPath("/ready"), true);
});

test("invite acceptance is public (pre-auth token-issuing flow)", () => {
  assert.equal(isPublicPath("/invites/abc123/accept"), true);
  assert.equal(isPublicPath("/invites"), false);
  assert.equal(isPublicPath("/invites/abc123"), false);
  assert.equal(isPublicPath("/invites/abc123/revoke"), false);
});

test("sensitive routes require auth at the edge", () => {
  assert.equal(isPublicPath("/auth/me"), false);
  assert.equal(isPublicPath("/content"), false);
  assert.equal(isPublicPath("/content/abc"), false);
  assert.equal(isPublicPath("/analytics/summary"), false);
  assert.equal(isPublicPath("/analytics/events"), false);
  assert.equal(isPublicPath("/assets"), false);
  assert.equal(isPublicPath("/generations"), false);
  assert.equal(isPublicPath("/brands"), false);
  assert.equal(isPublicPath("/invites"), false);
  assert.equal(isPublicPath("/playbooks"), false);
  assert.equal(isPublicPath("/orchestrator"), false);
});

test("pathnameOf strips the query string", () => {
  assert.equal(
    pathnameOf("/analytics/pixel.gif?tenant=demo&x=1"),
    "/analytics/pixel.gif",
  );
  assert.equal(pathnameOf("/content"), "/content");
});
