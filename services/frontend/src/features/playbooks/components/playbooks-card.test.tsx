import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    listPlaybooks: vi.fn(),
    createPlaybook: vi.fn(),
    activatePlaybook: vi.fn(),
  };
});

import { listPlaybooks, createPlaybook, activatePlaybook } from "../api";
import { PlaybooksCard } from "./playbooks-card";

const listPlaybooksMock = vi.mocked(listPlaybooks);
const createPlaybookMock = vi.mocked(createPlaybook);
const activatePlaybookMock = vi.mocked(activatePlaybook);

const activePlaybook = {
  id: "pb1",
  kind: "ARTICLE_OUTLINE" as const,
  name: "Default outlines",
  version: 2,
  system_template: "You are a senior content strategist.",
  is_active: true,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};
const inactivePlaybook = {
  ...activePlaybook,
  id: "pb0",
  name: "Old outlines",
  version: 1,
  is_active: false,
};

function renderCard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PlaybooksCard />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem("opengrow.token", "test-token");
  listPlaybooksMock.mockResolvedValue([activePlaybook, inactivePlaybook]);
});

describe("PlaybooksCard", () => {
  it("lists versions with the active one badged", async () => {
    renderCard();
    expect(await screen.findByText("Default outlines")).toBeInTheDocument();
    expect(screen.getByText("Old outlines")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("only shows an Activate button on inactive versions", async () => {
    renderCard();
    await screen.findByText("Default outlines");
    expect(screen.getAllByRole("button", { name: /activate/i })).toHaveLength(1);
  });

  it("activates a version", async () => {
    activatePlaybookMock.mockResolvedValue({ ...inactivePlaybook, is_active: true });
    const user = userEvent.setup();
    renderCard();

    await screen.findByText("Old outlines");
    await user.click(screen.getByRole("button", { name: /activate/i }));

    await waitFor(() => {
      expect(activatePlaybookMock).toHaveBeenCalledWith("pb0");
    });
  });

  it("creates a new version and shows a confirmation", async () => {
    const user = userEvent.setup();
    createPlaybookMock.mockResolvedValue({ ...inactivePlaybook, id: "pb2", version: 3 });
    renderCard();

    await screen.findByText("Default outlines");
    await user.type(screen.getByPlaceholderText(/seo-first outlines/i), "SEO-first outlines");
    await user.type(
      screen.getByPlaceholderText(/senior content strategist/i),
      "Custom playbook rules",
    );
    await user.click(screen.getByRole("button", { name: /save new version/i }));

    await waitFor(() => {
      expect(createPlaybookMock).toHaveBeenCalledWith({
        kind: "ARTICLE_OUTLINE",
        name: "SEO-first outlines",
        system_template: "Custom playbook rules",
      });
      expect(screen.getByText('Saved "SEO-first outlines" as a new version.')).toBeInTheDocument();
    });
  });

  it("shows the backend error when activation is rejected", async () => {
    activatePlaybookMock.mockRejectedValue(new Error("Only a tenant admin can manage playbooks"));
    const user = userEvent.setup();
    renderCard();

    await screen.findByText("Old outlines");
    await user.click(screen.getByRole("button", { name: /activate/i }));

    expect(
      await screen.findByText("Only a tenant admin can manage playbooks"),
    ).toBeInTheDocument();
  });

  it("shows an empty state when there are no custom versions", async () => {
    listPlaybooksMock.mockResolvedValue([]);
    renderCard();
    expect(
      await screen.findByText(/generation uses the built-in default/i),
    ).toBeInTheDocument();
  });
});
