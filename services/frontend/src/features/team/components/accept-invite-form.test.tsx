import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

const mutate = vi.fn();
const accept = { mutate, isPending: false, isError: false, error: null as Error | null };
vi.mock("../hooks", () => ({ useAcceptInvite: () => accept }));

import { AcceptInviteForm } from "./accept-invite-form";

function inputs(container: HTMLElement) {
  return {
    displayName: container.querySelector('input[autocomplete="name"]') as HTMLInputElement,
    password: container.querySelector('input[type="password"]') as HTMLInputElement,
  };
}

describe("AcceptInviteForm", () => {
  beforeEach(() => {
    push.mockClear();
    mutate.mockReset();
    accept.isError = false;
    accept.error = null;
  });

  it("submits the invite token with the new user's details and redirects", async () => {
    mutate.mockImplementation((_vars, opts) => opts.onSuccess({ tenant_slug: "acme" }));
    const user = userEvent.setup();
    const { container } = render(<AcceptInviteForm token="tok_abc123" />);
    const { displayName, password } = inputs(container);

    await user.type(displayName, "Teammate");
    await user.type(password, "supersecret");
    await user.click(screen.getByRole("button", { name: /join workspace/i }));

    expect(mutate).toHaveBeenCalledWith(
      { token: "tok_abc123", displayName: "Teammate", password: "supersecret" },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(push).toHaveBeenCalledWith("/app/acme");
  });

  it("shows the error message when accepting the invite fails", () => {
    accept.isError = true;
    accept.error = new Error("This invite has expired");
    render(<AcceptInviteForm token="tok_expired" />);
    expect(screen.getByText("This invite has expired")).toBeInTheDocument();
  });
});
