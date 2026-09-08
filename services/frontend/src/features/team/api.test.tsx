import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";

async function freshModules() {
  vi.resetModules();
  const auth = await import("@/lib/auth");
  const api = await import("./api");
  return { auth, api };
}

function pairResponse(): Response {
  return new Response(JSON.stringify({ access_token: "inv-access", refresh_token: "inv-refresh" }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("acceptInvite", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the pair in lite mode so the hook can store it", async () => {
    const { api } = await freshModules();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(pairResponse()));

    const { pair } = await api.acceptInvite({
      token: "tok",
      display_name: "Teammate",
      password: "secret",
    });
    expect(pair).toEqual({ access_token: "inv-access", refresh_token: "inv-refresh" });
  });

  it("returns null in cookie mode (gateway stripped the pair into cookies)", async () => {
    const { auth, api } = await freshModules();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(null, { status: 200, headers: { "x-og-auth": "cookie" } }),
      ),
    );

    const { pair } = await api.acceptInvite({
      token: "tok",
      display_name: "Teammate",
      password: "secret",
    });
    expect(pair).toBeNull();
    expect(auth.isCookieMode()).toBe(true);
  });

  it("surfaces the server error in cookie mode too", async () => {
    const { auth, api } = await freshModules();
    auth.setCookieMode(); // as readAuthMode would after a stripped response
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "This invite has expired" }), {
          status: 410,
          headers: { "Content-Type": "application/json", "x-og-auth": "cookie" },
        }),
      ),
    );

    await expect(
      api.acceptInvite({ token: "tok", display_name: "T", password: "secret" }),
    ).rejects.toThrow("This invite has expired");
  });
});
