import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";

// Fresh module state (cookie flag, inflight refresh, tried flag) per test.
async function freshModules() {
  vi.resetModules();
  const auth = await import("./auth");
  const http = await import("./http");
  return { auth, http };
}

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

describe("http transport — auth mode", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("readAuthMode() enters cookie mode only when the gateway header is present", async () => {
    const { auth, http } = await freshModules();
    http.readAuthMode(jsonResponse({}, { headers: { "x-og-auth": "cookie" } }));
    expect(auth.isCookieMode()).toBe(true);

    const { auth: auth2, http: http2 } = await freshModules();
    http2.readAuthMode(jsonResponse({}));
    expect(auth2.isCookieMode()).toBe(false);
  });

  it("lite refresh parses the token pair body and stores it", async () => {
    const { auth, http } = await freshModules();
    localStorage.setItem("opengrow.refresh", "old-refresh");
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ access_token: "new-access", refresh_token: "new-refresh" }),
    );
    vi.stubGlobal("fetch", fetchMock);

    expect(await http.refreshSession()).toBe(true);
    expect(localStorage.getItem("opengrow.token")).toBe("new-access");
    expect(localStorage.getItem("opengrow.refresh")).toBe("new-refresh");
    expect(auth.isCookieMode()).toBe(false);
    const [, init] = fetchMock.mock.calls[0];
    expect((init as RequestInit).credentials).toBe("include");
    expect((init as RequestInit).body).toBe(JSON.stringify({ refresh_token: "old-refresh" }));
  });

  it("cookie-mode refresh succeeds on a stripped (empty) body and stores nothing", async () => {
    const { auth, http } = await freshModules();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, {
        status: 200,
        headers: { "x-og-auth": "cookie" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    expect(await http.refreshSession()).toBe(true);
    expect(auth.isCookieMode()).toBe(true);
    expect(localStorage.getItem("opengrow.token")).toBeNull();
    expect(localStorage.getItem("opengrow.refresh")).toBeNull();
  });

  it("cookie-mode refresh failure clears the BFF cookies best-effort", async () => {
    const { auth, http } = await freshModules();
    auth.setCookieMode();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 })) // refresh
      .mockResolvedValueOnce(new Response(null, { status: 204 })); // logout
    vi.stubGlobal("fetch", fetchMock);

    expect(await http.refreshSession()).toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][0]).toBe("http://localhost:8000/auth/logout");
    expect((fetchMock.mock.calls[1][1] as RequestInit).credentials).toBe("include");
  });

  it("ensureSession() silently restores a cookie session after reload", async () => {
    const { auth, http } = await freshModules();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, { status: 200, headers: { "x-og-auth": "cookie" } }),
    );
    vi.stubGlobal("fetch", fetchMock);

    expect(await http.ensureSession()).toBe(true);
    expect(auth.isCookieMode()).toBe(true);
    // Second call is a no-op (single attempt) and reports the existing session.
    expect(await http.ensureSession()).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("ensureSession() returns false in lite mode without a usable refresh token", async () => {
    const { http } = await freshModules();
    // Lite core rejects an empty refresh body with a 4xx — no session restores.
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "field required" }), { status: 422 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    expect(await http.ensureSession()).toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("apiGet sends credentials and the Bearer header (lite)", async () => {
    const { http } = await freshModules();
    localStorage.setItem("opengrow.token", "tok");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await http.apiGet("/auth/me");
    const [, init] = fetchMock.mock.calls[0];
    expect((init as RequestInit).credentials).toBe("include");
    expect(((init as RequestInit).headers as Record<string, string>).Authorization).toBe(
      "Bearer tok",
    );
  });
});
