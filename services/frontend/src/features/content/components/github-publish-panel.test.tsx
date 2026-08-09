import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ContentPiece, Publication } from "../api";
import { loadLastUsed } from "../publish-form.mjs";

let publishResult: Publication;
let refreshResult: Publication;
const publishMutate = vi.fn(
  (_input: unknown, opts?: { onSuccess?: (p: Publication) => void }) =>
    opts?.onSuccess?.(publishResult),
);
const refreshMutate = vi.fn(
  (_id: unknown, opts?: { onSuccess?: (p: Publication) => void }) =>
    opts?.onSuccess?.(refreshResult),
);
let config: Record<string, unknown> | undefined;
let pubs: Publication[] | undefined;

vi.mock("../hooks", () => ({
  usePublishGithub: () => ({ mutate: publishMutate, isPending: false, error: null }),
  useRefreshPublication: () => ({ mutate: refreshMutate, isPending: false, error: null }),
  useGitHubPublishConfig: () => ({ data: config }),
  usePublications: () => ({ data: pubs }),
}));

import { GitHubPublishPanel } from "./github-publish-panel";

function content(overrides: Partial<ContentPiece> = {}): ContentPiece {
  return {
    id: "c1",
    title: "Launch post",
    body: "# Body",
    format: "markdown",
    status: "APPROVED",
    source_generation_id: null,
    next_action: null,
    due_at: null,
    created_at: "2026-07-26T00:00:00Z",
    updated_at: "2026-07-26T00:00:00Z",
    ...overrides,
  };
}

function pub(overrides: Partial<Publication> = {}): Publication {
  return {
    id: "p1",
    content_piece_id: "c1",
    channel: "GITHUB_PR",
    status: "PR_OPENED",
    url: "https://github.com/o/n/pull/7",
    external_ref: "PR #7 (opengrow/c1)",
    error_message: null,
    target: { pr_number: 7, state: "open", merged: false },
    created_at: "2026-07-26T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  publishMutate.mockClear();
  refreshMutate.mockClear();
  localStorage.clear();
  config = { configured: true, source: "tenant", token_last4: "1234" };
  pubs = [];
  publishResult = pub();
  refreshResult = pub();
});

describe("GitHubPublishPanel — connection state", () => {
  it("renders the publish form when configured", () => {
    render(<GitHubPublishPanel content={content()} slug="demo" onMessage={vi.fn()} />);
    expect(screen.getByRole("heading", { name: /github publish/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("owner/repo")).toBeInTheDocument();
  });

  it("shows a connect-in-settings notice when not configured", () => {
    config = { configured: false };
    render(<GitHubPublishPanel content={content()} slug="demo" onMessage={vi.fn()} />);
    expect(screen.getByText(/connect github in settings/i)).toBeInTheDocument();
  });

  it("shows a CHECKING state (not READY) while config is loading", () => {
    config = undefined;
    render(<GitHubPublishPanel content={content()} slug="demo" onMessage={vi.fn()} />);
    expect(screen.getByText(/checking/i)).toBeInTheDocument();
    expect(screen.queryByText("READY")).toBeNull();
    expect(screen.queryByText(/connect github in settings/i)).toBeNull();
  });
});

describe("GitHubPublishPanel — publications list", () => {
  it("renders PR number, a Merged badge, and a timestamp", () => {
    pubs = [
      pub({ status: "PUBLISHED", target: { pr_number: 7, state: "closed", merged: true } }),
    ];
    render(<GitHubPublishPanel content={content()} slug="demo" onMessage={vi.fn()} />);
    expect(screen.getByText("PR #7")).toBeInTheDocument();
    expect(screen.getByText("Merged")).toBeInTheDocument();
  });

  it("collapses duplicate publications for the same PR into one row", () => {
    pubs = [
      pub({ id: "p1", created_at: "2026-07-26T00:00:00Z" }),
      pub({ id: "p2", created_at: "2026-07-26T01:00:00Z" }),
    ];
    render(<GitHubPublishPanel content={content()} slug="demo" onMessage={vi.fn()} />);
    expect(screen.getAllByText("PR #7")).toHaveLength(1);
  });

  it("offers Refresh on a FAILED publication (not only PR_OPENED)", () => {
    pubs = [pub({ status: "FAILED", url: null, error_message: "boom", target: {} })];
    render(<GitHubPublishPanel content={content()} slug="demo" onMessage={vi.fn()} />);
    expect(screen.getByRole("button", { name: /refresh status/i })).toBeInTheDocument();
  });

  it("shows an empty state when there are no publications", () => {
    pubs = [];
    render(<GitHubPublishPanel content={content()} slug="demo" onMessage={vi.fn()} />);
    expect(screen.getByText(/no publications yet/i)).toBeInTheDocument();
  });
});

describe("GitHubPublishPanel — validation & submit", () => {
  it("blocks submit and shows an inline error for a malformed repo", async () => {
    const user = userEvent.setup();
    render(<GitHubPublishPanel content={content()} slug="demo" onMessage={vi.fn()} />);
    await user.type(screen.getByPlaceholderText("owner/repo"), "noslash");
    await user.click(screen.getByRole("button", { name: /open pr/i }));
    expect(screen.getByText(/format owner\/name/i)).toBeInTheDocument();
    expect(publishMutate).not.toHaveBeenCalled();
  });

  it("sends draft, labels, and reviewers on a valid publish", async () => {
    const user = userEvent.setup();
    render(<GitHubPublishPanel content={content()} slug="demo" onMessage={vi.fn()} />);
    await user.type(screen.getByPlaceholderText("owner/repo"), "owner/name");
    await user.click(screen.getByLabelText(/open as a draft pr/i));
    await user.type(screen.getByPlaceholderText(/labels/i), "docs, seo");
    await user.type(screen.getByPlaceholderText(/reviewers/i), "alice");
    await user.click(screen.getByRole("button", { name: /open pr/i }));
    expect(publishMutate).toHaveBeenCalledTimes(1);
    expect(publishMutate.mock.calls[0][0]).toMatchObject({
      repo: "owner/name",
      draft: true,
      labels: ["docs", "seo"],
      reviewers: ["alice"],
    });
  });

  it("surfaces non-fatal warnings from a successful publish", async () => {
    const onMessage = vi.fn();
    publishResult = pub({ target: { pr_number: 7, warnings: ["Could not apply labels (500)."] } });
    const user = userEvent.setup();
    render(<GitHubPublishPanel content={content()} slug="demo" onMessage={onMessage} />);
    await user.type(screen.getByPlaceholderText("owner/repo"), "owner/name");
    await user.click(screen.getByRole("button", { name: /open pr/i }));
    const msg = onMessage.mock.calls.map((c) => c[0]).filter(Boolean).join(" ");
    expect(msg).toMatch(/Could not apply labels/);
  });

  it("persists the last-used repo and seeds it on next mount", async () => {
    const user = userEvent.setup();
    const { unmount } = render(
      <GitHubPublishPanel content={content()} slug="demo" onMessage={vi.fn()} />,
    );
    await user.type(screen.getByPlaceholderText("owner/repo"), "owner/blog");
    await user.click(screen.getByRole("button", { name: /open pr/i }));
    expect(loadLastUsed("demo")).toMatchObject({ repo: "owner/blog" });
    unmount();
    render(<GitHubPublishPanel content={content({ id: "c2" })} slug="demo" onMessage={vi.fn()} />);
    expect((screen.getByPlaceholderText("owner/repo") as HTMLInputElement).value).toBe(
      "owner/blog",
    );
  });

  it("reports content marked Published when a refresh finds the PR merged", async () => {
    const onMessage = vi.fn();
    pubs = [pub()];
    refreshResult = pub({ status: "PUBLISHED", target: { pr_number: 7, merged: true } });
    const user = userEvent.setup();
    render(<GitHubPublishPanel content={content()} slug="demo" onMessage={onMessage} />);
    await user.click(screen.getByRole("button", { name: /refresh status/i }));
    const msg = onMessage.mock.calls.map((c) => c[0]).filter(Boolean).join(" ");
    expect(msg).toMatch(/Published/);
  });
});
