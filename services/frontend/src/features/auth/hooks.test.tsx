import { describe, it, expect, beforeEach, vi } from "vitest";

const mutationFns: Array<(vars: { email: string; password: string }) => Promise<unknown>> = [];
vi.mock("@tanstack/react-query", () => ({
  useMutation: (opts: { mutationFn: (typeof mutationFns)[number] }) => {
    mutationFns.push(opts.mutationFn);
    return { mutate: vi.fn(), isPending: false };
  },
  useQuery: () => ({ data: undefined }),
}));

const login = vi.fn();
const fetchMe = vi.fn();
vi.mock("./api", () => ({ login: (...a: unknown[]) => login(...a), fetchMe: () => fetchMe() }));

import { useLogin } from "./hooks";

describe("useLogin", () => {
  beforeEach(() => {
    mutationFns.length = 0;
    login.mockReset();
    fetchMe.mockReset();
    localStorage.clear();
    vi.resetModules();
  });

  it("stores the token pair in lite mode (gateway returned a pair)", async () => {
    login.mockResolvedValue({ pair: { access_token: "a", refresh_token: "r" } });
    fetchMe.mockResolvedValue({ id: "u1" });

    useLogin();
    const me = await mutationFns[0]({ email: "a@b.com", password: "secret" });

    expect(me).toEqual({ id: "u1" });
    expect(localStorage.getItem("opengrow.token")).toBe("a");
    expect(localStorage.getItem("opengrow.refresh")).toBe("r");
  });

  it("saves nothing in cookie mode (gateway stripped the pair into cookies)", async () => {
    login.mockResolvedValue({ pair: null });
    fetchMe.mockResolvedValue({ id: "u1" });

    useLogin();
    const me = await mutationFns[0]({ email: "a@b.com", password: "secret" });

    expect(me).toEqual({ id: "u1" }); // fetchMe still runs — the cookie rides along
    expect(localStorage.getItem("opengrow.token")).toBeNull();
    expect(localStorage.getItem("opengrow.refresh")).toBeNull();
  });
});
