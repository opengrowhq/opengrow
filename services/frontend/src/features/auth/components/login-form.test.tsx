import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
let nextParam: string | null = null;
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
  useSearchParams: () => ({ get: () => nextParam }),
}));

const mutate = vi.fn();
const login = { mutate, isPending: false, isError: false, error: null as Error | null };
vi.mock("../hooks", () => ({ useLogin: () => login }));

import { LoginForm } from "./login-form";

function inputs(container: HTMLElement) {
  return {
    email: container.querySelector('input[type="email"]') as HTMLInputElement,
    password: container.querySelector('input[type="password"]') as HTMLInputElement,
  };
}

describe("LoginForm", () => {
  beforeEach(() => {
    push.mockClear();
    mutate.mockReset();
    nextParam = null;
    login.isError = false;
    login.error = null;
  });

  it("submits credentials and redirects to the workspace on success", async () => {
    mutate.mockImplementation((_vars, opts) => opts.onSuccess({ tenant_slug: "acme" }));
    const user = userEvent.setup();
    const { container } = render(<LoginForm />);
    const { email, password } = inputs(container);

    await user.clear(email);
    await user.type(email, "a@b.com");
    await user.type(password, "secret");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(mutate).toHaveBeenCalledWith(
      { email: "a@b.com", password: "secret" },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(push).toHaveBeenCalledWith("/app/acme");
  });

  it("honors ?next=onboarding after login", async () => {
    nextParam = "onboarding";
    mutate.mockImplementation((_vars, opts) => opts.onSuccess({ tenant_slug: "acme" }));
    const user = userEvent.setup();
    const { container } = render(<LoginForm />);
    const { password } = inputs(container);

    await user.type(password, "secret"); // email has a default value; password is required
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(push).toHaveBeenCalledWith("/app/acme/onboarding");
  });

  it("shows the error message when login fails", () => {
    login.isError = true;
    login.error = new Error("Invalid credentials");
    render(<LoginForm />);
    expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
  });
});
