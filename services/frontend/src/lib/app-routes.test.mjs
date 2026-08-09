import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  appPath,
  appRootPath,
  resolvePostAuthPath,
  tenantSlugOrDemo,
} from "./app-routes.mjs";

describe("tenant app routes", () => {
  it("uses the tenant slug under /app", () => {
    assert.equal(appRootPath("demo"), "/app/demo");
    assert.equal(appPath("acme", "content"), "/app/acme/content");
  });

  it("falls back to demo while auth data is loading", () => {
    assert.equal(tenantSlugOrDemo(undefined), "demo");
    assert.equal(appPath("", "brand"), "/app/demo/brand");
  });

  it("encodes dynamic path segments", () => {
    assert.equal(
      appPath("new brand", "content", "piece/1"),
      "/app/new%20brand/content/piece%2F1",
    );
  });
});

describe("resolvePostAuthPath", () => {
  it("routes the onboarding hint to the tenant onboarding page", () => {
    assert.equal(resolvePostAuthPath("onboarding", "acme"), "/app/acme/onboarding");
  });

  it("passes through safe in-app paths", () => {
    assert.equal(resolvePostAuthPath("/app/acme/content", "acme"), "/app/acme/content");
  });

  it("falls back to workspace home without a hint", () => {
    assert.equal(resolvePostAuthPath(undefined, "acme"), "/app/acme");
    assert.equal(resolvePostAuthPath("", "acme"), "/app/acme");
  });

  it("refuses external/open-redirect targets", () => {
    assert.equal(resolvePostAuthPath("//evil.com", "acme"), "/app/acme");
    assert.equal(resolvePostAuthPath("https://evil.com", "acme"), "/app/acme");
    assert.equal(resolvePostAuthPath("/settings", "acme"), "/app/acme");
  });
});
