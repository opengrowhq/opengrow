import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "@/lib/http";

vi.mock("@/features/content/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/content/api")>();
  return {
    ...actual,
    getGitHubPublishConfig: vi.fn(),
    upsertGitHubCredential: vi.fn(),
    deleteGitHubCredential: vi.fn(),
  };
});

import {
  getGitHubPublishConfig,
  upsertGitHubCredential,
  deleteGitHubCredential,
} from "@/features/content/api";
import { GitHubConnectionCard } from "./github-connection-card";

const getConfigMock = vi.mocked(getGitHubPublishConfig);
const upsertMock = vi.mocked(upsertGitHubCredential);
const deleteMock = vi.mocked(deleteGitHubCredential);

const disconnected = {
  configured: false,
  api_url: "https://api.github.com",
  source: null,
  has_tenant_credential: false,
  token_last4: null,
};
const instance = { ...disconnected, configured: true, source: "env" };
const workspace = {
  ...disconnected,
  configured: true,
  source: "tenant",
  has_tenant_credential: true,
  token_last4: "1234",
};

function renderCard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <GitHubConnectionCard />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem("opengrow.token", "test-token");
});

describe("GitHubConnectionCard", () => {
  it("shows the not-connected state when nothing is configured", async () => {
    getConfigMock.mockResolvedValue(disconnected);
    renderCard();
    expect(await screen.findByText("NOT CONNECTED")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Connect GitHub" })).toBeInTheDocument();
    expect(screen.queryByText(/Disconnect workspace token/)).not.toBeInTheDocument();
  });

  it("shows the instance-token state when configured via env", async () => {
    getConfigMock.mockResolvedValue(instance);
    renderCard();
    expect(await screen.findByText("INSTANCE TOKEN")).toBeInTheDocument();
    expect(screen.getByText(/Connected via the instance token/)).toBeInTheDocument();
  });

  it("shows the workspace state with a masked token", async () => {
    getConfigMock.mockResolvedValue(workspace);
    renderCard();
    expect(await screen.findByText("WORKSPACE TOKEN")).toBeInTheDocument();
    expect(screen.getByText(/••••1234/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Disconnect workspace token" }),
    ).toBeInTheDocument();
  });

  it("saves a trimmed token and refetches the config on success", async () => {
    getConfigMock.mockResolvedValue(disconnected);
    upsertMock.mockResolvedValue({
      configured: true,
      source: "tenant",
      token_last4: "9abc",
      display_name: null,
      api_url: "https://api.github.com",
    });
    renderCard();
    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("github_pat_…"), "  ghp_secret  ");
    await user.click(screen.getByRole("button", { name: "Connect GitHub" }));

    expect(await screen.findByText(/GitHub connected/)).toBeInTheDocument();
    expect(upsertMock).toHaveBeenCalledWith({ token: "ghp_secret" }, expect.anything());
    expect((screen.getByPlaceholderText("github_pat_…") as HTMLInputElement).value).toBe("");
    // Initial fetch + refetch from invalidating ["github-publish-config"].
    await waitFor(() => expect(getConfigMock).toHaveBeenCalledTimes(2));
  });

  it("surfaces the server error detail when GitHub rejects the token", async () => {
    getConfigMock.mockResolvedValue(disconnected);
    upsertMock.mockRejectedValue(new ApiError(400, "GitHub rejected the token"));
    renderCard();
    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("github_pat_…"), "ghp_bad");
    await user.click(screen.getByRole("button", { name: "Connect GitHub" }));

    expect(await screen.findByText("GitHub rejected the token")).toBeInTheDocument();
  });

  it("shows the stored display name from config on reload", async () => {
    getConfigMock.mockResolvedValue({ ...workspace, display_name: "Main PAT" });
    renderCard();
    expect(await screen.findByText(/Main PAT/)).toBeInTheDocument();
  });

  it("shows a verifying-token affordance while the connect request is in flight", async () => {
    getConfigMock.mockResolvedValue(disconnected);
    upsertMock.mockReturnValue(new Promise(() => {})); // never resolves → stays pending
    renderCard();
    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("github_pat_…"), "ghp_secret");
    await user.click(screen.getByRole("button", { name: "Connect GitHub" }));
    expect(await screen.findByText(/verifying token/i)).toBeInTheDocument();
  });

  it("disconnects the workspace token after a confirm step", async () => {
    getConfigMock.mockResolvedValue(workspace);
    deleteMock.mockResolvedValue(undefined);
    renderCard();
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole("button", { name: "Disconnect workspace token" }),
    );
    await user.click(screen.getByRole("button", { name: "Confirm disconnect" }));

    expect(await screen.findByText(/Workspace token removed/)).toBeInTheDocument();
    expect(deleteMock).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(getConfigMock).toHaveBeenCalledTimes(2));
  });
});
