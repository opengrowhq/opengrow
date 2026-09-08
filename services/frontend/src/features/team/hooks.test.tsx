import { describe, it, expect, beforeEach, vi } from "vitest";

const mutationFns: Array<
  (vars: { token: string; displayName: string; password: string }) => Promise<unknown>
> = [];
vi.mock("@tanstack/react-query", () => ({
  useMutation: (opts: { mutationFn: (typeof mutationFns)[number] }) => {
    mutationFns.push(opts.mutationFn);
    return { mutate: vi.fn(), isPending: false };
  },
  useQuery: () => ({ data: undefined }),
}));

const acceptInvite = vi.fn();
const fetchMe = vi.fn();
vi.mock("./api", () => ({
  acceptInvite: (...a: unknown[]) => acceptInvite(...a),
  createInvite: vi.fn(),
  listInvites: vi.fn(),
  listMembers: vi.fn(),
  removeMember: vi.fn(),
  revokeInvite: vi.fn(),
}));
vi.mock("@/features/auth/api", () => ({ fetchMe: () => fetchMe() }));

import { useAcceptInvite } from "./hooks";

describe("useAcceptInvite", () => {
  beforeEach(() => {
    mutationFns.length = 0;
    acceptInvite.mockReset();
    fetchMe.mockReset();
    localStorage.clear();
    vi.resetModules();
  });

  it("stores the returned access token in lite mode", async () => {
    acceptInvite.mockResolvedValue({ pair: { access_token: "inv-access" } });
    fetchMe.mockResolvedValue({ id: "u1" });

    useAcceptInvite();
    const me = await mutationFns[0]({ token: "tok", displayName: "T", password: "secret" });

    expect(me).toEqual({ id: "u1" });
    expect(localStorage.getItem("opengrow.token")).toBe("inv-access");
  });

  it("saves nothing in cookie mode (gateway already set the cookies)", async () => {
    acceptInvite.mockResolvedValue({ pair: null });
    fetchMe.mockResolvedValue({ id: "u1" });

    useAcceptInvite();
    const me = await mutationFns[0]({ token: "tok", displayName: "T", password: "secret" });

    expect(me).toEqual({ id: "u1" });
    expect(localStorage.getItem("opengrow.token")).toBeNull();
  });
});
