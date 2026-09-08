import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
}));

const ensureSession = vi.fn();
vi.mock("@/lib/http", () => ({ ensureSession: (...a: unknown[]) => ensureSession(...a) }));

import { hasSession } from "@/lib/auth";
import { useAuthGuard } from "./use-auth-guard";

function Probe() {
  return <div data-testid="probe">{useAuthGuard() ? "in" : "out"}</div>;
}

describe("useAuthGuard", () => {
  beforeEach(() => {
    replace.mockReset();
    ensureSession.mockReset();
    localStorage.clear();
  });

  it("redirects to /login when ensureSession cannot restore a session", async () => {
    ensureSession.mockResolvedValue(false);
    render(<Probe />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });

  it("does not redirect when a cookie session is silently restored", async () => {
    ensureSession.mockResolvedValue(true);
    render(<Probe />);
    await waitFor(() => expect(ensureSession).toHaveBeenCalledTimes(1));
    expect(replace).not.toHaveBeenCalled();
  });

  it("does not redirect when a lite-mode token exists", async () => {
    localStorage.setItem("opengrow.token", "tok");
    ensureSession.mockResolvedValue(false);
    render(<Probe />);
    await new Promise((r) => setTimeout(r, 20));
    expect(replace).not.toHaveBeenCalled();
    expect(ensureSession).not.toHaveBeenCalled();
  });
});

describe("useHasToken", () => {
  it("reflects the session under both transports", () => {
    localStorage.clear();
    expect(hasSession()).toBe(false);
    localStorage.setItem("opengrow.token", "tok");
    expect(hasSession()).toBe(true);
  });
});
