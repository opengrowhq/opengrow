import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

const mutate = vi.fn();
const signup = { mutate, isPending: false, isError: false, error: null as Error | null };
vi.mock("../hooks", () => ({ useSignup: () => signup }));

import { SignupForm } from "./signup-form";

function inputs(container: HTMLElement) {
  return {
    tenantName: container.querySelector('input[autocomplete="organization"]') as HTMLInputElement,
    displayName: container.querySelector('input[autocomplete="name"]') as HTMLInputElement,
    email: container.querySelector('input[type="email"]') as HTMLInputElement,
    password: container.querySelector('input[type="password"]') as HTMLInputElement,
  };
}

describe("SignupForm", () => {
  beforeEach(() => {
    push.mockClear();
    mutate.mockReset();
    signup.isError = false;
    signup.error = null;
  });

  it("submits the workspace details and redirects to the new workspace", async () => {
    mutate.mockImplementation((_vars, opts) => opts.onSuccess({ tenant_slug: "acme" }));
    const user = userEvent.setup();
    const { container } = render(<SignupForm />);
    const { tenantName, displayName, email, password } = inputs(container);

    await user.type(tenantName, "Acme Inc");
    await user.type(displayName, "Founder");
    await user.type(email, "founder@acme.com");
    await user.type(password, "supersecret");
    await user.click(screen.getByRole("button", { name: /create workspace/i }));

    expect(mutate).toHaveBeenCalledWith(
      {
        tenant_name: "Acme Inc",
        display_name: "Founder",
        email: "founder@acme.com",
        password: "supersecret",
      },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(push).toHaveBeenCalledWith("/app/acme");
  });

  it("shows the error message when signup fails", () => {
    signup.isError = true;
    signup.error = new Error("An account with this email already exists");
    render(<SignupForm />);
    expect(
      screen.getByText("An account with this email already exists"),
    ).toBeInTheDocument();
  });
});
