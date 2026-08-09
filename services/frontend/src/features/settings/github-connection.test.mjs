import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  cleanGitHubCredentialInput,
  githubConnectionState,
  githubConnectionStatus,
  maskedToken,
} from "./github-connection.mjs";

const base = {
  configured: false,
  api_url: "https://api.github.com",
  source: null,
  has_tenant_credential: false,
  token_last4: null,
};

describe("github connection state", () => {
  it("is disconnected when nothing is configured", () => {
    assert.equal(githubConnectionState(base), "disconnected");
    assert.equal(githubConnectionState(undefined), "disconnected");
  });

  it("is instance when configured via the env token", () => {
    assert.equal(
      githubConnectionState({ ...base, configured: true, source: "env" }),
      "instance",
    );
  });

  it("is workspace when a tenant credential is stored", () => {
    assert.equal(
      githubConnectionState({
        ...base,
        configured: true,
        source: "tenant",
        has_tenant_credential: true,
        token_last4: "1234",
      }),
      "workspace",
    );
  });

  it("derives a label and tone per state", () => {
    assert.deepEqual(githubConnectionStatus(base), {
      state: "disconnected",
      label: "Not connected",
      tone: "neutral",
    });
    assert.deepEqual(githubConnectionStatus({ ...base, configured: true, source: "tenant" }), {
      state: "workspace",
      label: "Workspace token",
      tone: "success",
    });
    assert.deepEqual(githubConnectionStatus({ ...base, configured: true, source: "env" }), {
      state: "instance",
      label: "Instance token",
      tone: "info",
    });
  });
});

describe("maskedToken", () => {
  it("masks the last 4 characters", () => {
    assert.equal(maskedToken("1234"), "••••1234");
    assert.equal(maskedToken("  ab12 "), "••••ab12");
  });

  it("is empty without a tail", () => {
    assert.equal(maskedToken(null), "");
    assert.equal(maskedToken("   "), "");
  });
});

describe("cleanGitHubCredentialInput", () => {
  it("trims the token and optional display name", () => {
    assert.deepEqual(
      cleanGitHubCredentialInput({ token: "  ghp_abc  ", display_name: " My PAT " }),
      { ok: true, body: { token: "ghp_abc", display_name: "My PAT" } },
    );
  });

  it("omits a blank display name", () => {
    assert.deepEqual(cleanGitHubCredentialInput({ token: "ghp_abc", display_name: "  " }), {
      ok: true,
      body: { token: "ghp_abc" },
    });
  });

  it("rejects an empty token", () => {
    const result = cleanGitHubCredentialInput({ token: "   " });
    assert.equal(result.ok, false);
    assert.match(result.error, /personal access token/);
  });
});
