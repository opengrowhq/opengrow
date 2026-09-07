import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
let nextParam: string | null = null;
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(nextParam ? { next: nextParam } : {}),
}));

const mutate = vi.fn();
const login = { mutate, isPending: false, isError: false, error: null as Error | null };
vi.mock("../hooks", () => ({ useLogin: () => login }));

const fetchMe = vi.fn();
vi.mock("../api", () => ({ fetchMe: (...args: unknown[]) => fetchMe(...args) }));

const isGoogleLoginAvailable = vi.fn();
vi.mock("../oauth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../oauth")>();
  return { ...actual, isGoogleLoginAvailable: (...a: unknown[]) => isGoogleLoginAvailable(...a) };
});

import { LoginForm } from "./login-form";
import { GOOGLE_LOGIN_URL } from "../oauth";

function renderForm() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <LoginForm />
    </QueryClientProvider>,
  );
}

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
    fetchMe.mockReset();
    isGoogleLoginAvailable.mockReset();
    isGoogleLoginAvailable.mockResolvedValue(false);
    nextParam = null;
    login.isError = false;
    login.error = null;
    window.localStorage.clear();
    window.history.replaceState(null, "", "/login");
  });

  it("submits credentials and redirects to the workspace on success", async () => {
    mutate.mockImplementation((_vars, opts) => opts.onSuccess({ tenant_slug: "acme" }));
    const user = userEvent.setup();
    const { container } = renderForm();
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
    const { container } = renderForm();
    const { password } = inputs(container);

    await user.type(password, "secret"); // email has a default value; password is required
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(push).toHaveBeenCalledWith("/app/acme/onboarding");
  });

  it("shows the error message when login fails", () => {
    login.isError = true;
    login.error = new Error("Invalid credentials");
    renderForm();
    expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
  });

  it("hides the Google button when the backend has no OAuth router", () => {
    renderForm();
    expect(screen.queryByRole("link", { name: /continue with google/i })).not.toBeInTheDocument();
  });

  it("shows the Google button pointing at the backend login endpoint when available", async () => {
    isGoogleLoginAvailable.mockResolvedValue(true);
    renderForm();
    const link = await screen.findByRole("link", { name: /continue with google/i });
    expect(link).toHaveAttribute("href", GOOGLE_LOGIN_URL);
  });

  it("consumes the OAuth token fragment, stores it, and lands in the workspace", async () => {
    window.history.replaceState(null, "", "/login#access_token=tok&refresh_token=ref");
    fetchMe.mockResolvedValue({ tenant_slug: "acme" });
    renderForm();

    await vi.waitFor(() => expect(push).toHaveBeenCalledWith("/app/acme"));
    expect(window.localStorage.getItem("opengrow.token")).toBe("tok");
    expect(window.localStorage.getItem("opengrow.refresh")).toBe("ref");
    expect(window.location.hash).toBe("");
    expect(push).toHaveBeenCalledWith("/app/acme");
  });

  it("shows a friendly error when the OAuth callback failed", () => {
    window.history.replaceState(null, "", "/login?error=state_invalid");
    renderForm();
    expect(screen.getByText("Google sign-in failed. Please try again.")).toBeInTheDocument();
  });
});
