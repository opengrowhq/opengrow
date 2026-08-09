import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

vi.mock("@/components/ui/app-shell", () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/features/auth", () => ({
  useAuthGuard: () => true,
  useMe: () => ({ data: { tenant_slug: "demo" } }),
}));
vi.mock("@/features/brand", () => ({ useBrands: () => ({ data: [] }) }));

// Id-aware generation store: mutate assigns a fresh id via onSuccess, and the
// query hook only returns data for that id — mirrors the real hooks so stale
// outline/draft state is exercised honestly.
type Gen = { status: string; result: string | null; error_message: string | null };
const generations: Record<string, Gen> = {};
let idSeq = 0;

const createMutate = vi.fn();
let failNextCreate = false;
createMutate.mockImplementation(
  (
    _body: unknown,
    opts?: {
      onSuccess?: (g: { id: string }) => void;
      onError?: (e: Error) => void;
      onSettled?: () => void;
    },
  ) => {
    if (failNextCreate) {
      failNextCreate = false;
      opts?.onError?.(new Error("boom"));
    } else {
      opts?.onSuccess?.({ id: `gen-${++idSeq}` });
    }
    opts?.onSettled?.();
  },
);
vi.mock("../hooks", () => ({
  useCreateArticleGeneration: () => ({ mutate: createMutate, isPending: false, error: null }),
  useArticleGeneration: (id: string | null) => ({ data: id ? generations[id] : undefined }),
}));

const saveMutate = vi.fn();
vi.mock("@/features/content", () => ({
  useCreateFromGeneration: () => ({ mutate: saveMutate, isPending: false }),
}));

const createRunMutate = vi.fn();
vi.mock("../orchestrator-hooks", () => ({
  useCreateOrchestratorRun: () => ({ mutate: createRunMutate, isPending: false, error: null }),
  useOrchestratorRuns: () => ({ data: [], isLoading: false }),
  useOrchestratorRun: () => ({ data: undefined }),
  useApproveOrchestratorOutline: () => ({ mutate: vi.fn(), isPending: false, error: null }),
  useResumeOrchestratorRun: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { ArticleStudio } from "./article-studio";

beforeEach(() => {
  createMutate.mockClear();
  saveMutate.mockClear();
  createRunMutate.mockClear();
  push.mockClear();
  for (const key of Object.keys(generations)) delete generations[key];
  idSeq = 0;
});

async function planArticle(user: ReturnType<typeof userEvent.setup>, topic = "Why founders blog") {
  await user.type(screen.getByLabelText(/topic/i), topic);
  await user.click(screen.getByRole("button", { name: /plan article/i }));
  return `gen-${idSeq}`;
}

describe("ArticleStudio", () => {
  it("renders the article brief form", () => {
    render(<ArticleStudio />);
    expect(screen.getByRole("heading", { name: /article/i })).toBeInTheDocument();
  });

  it("blocks generation and shows an inline error when the topic is empty", async () => {
    const user = userEvent.setup();
    render(<ArticleStudio />);
    await user.click(screen.getByRole("button", { name: /plan article/i }));
    expect(screen.getByText(/enter a topic/i)).toBeInTheDocument();
    expect(createMutate).not.toHaveBeenCalled();
  });

  it("clears a field's validation error as soon as the user edits it", async () => {
    const user = userEvent.setup();
    render(<ArticleStudio />);
    await user.click(screen.getByRole("button", { name: /plan article/i }));
    expect(screen.getByText(/enter a topic/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText(/topic/i), "W");
    expect(screen.queryByText(/enter a topic/i)).not.toBeInTheDocument();
  });

  it("derives the slug from the topic until the user edits it by hand", async () => {
    const user = userEvent.setup();
    render(<ArticleStudio />);
    await user.type(screen.getByLabelText(/topic/i), "Why Founders Blog");
    expect(screen.getByLabelText(/slug/i)).toHaveValue("why-founders-blog");

    // A manual slug wins over the derivation from then on.
    await user.clear(screen.getByLabelText(/slug/i));
    await user.type(screen.getByLabelText(/slug/i), "custom-slug");
    await user.type(screen.getByLabelText(/topic/i), " v2");
    expect(screen.getByLabelText(/slug/i)).toHaveValue("custom-slug");
  });

  it("runs the brief through the orchestrator with the review preference", async () => {
    const user = userEvent.setup();
    render(<ArticleStudio />);
    await user.type(screen.getByLabelText(/topic/i), "Why founders blog");
    await user.click(screen.getByRole("checkbox", { name: /review outline before drafting/i }));
    await user.click(screen.getByRole("button", { name: /run with orchestrator/i }));
    expect(createRunMutate).toHaveBeenCalledTimes(1);
    const body = createRunMutate.mock.calls[0][0];
    expect(body.article.topic).toBe("Why founders blog");
    expect(body.pause_for_outline_approval).toBe(false);
  });

  it("sends a cleaned article brief with kind=article_outline", async () => {
    const user = userEvent.setup();
    render(<ArticleStudio />);
    await user.type(screen.getByLabelText(/topic/i), "Why founders blog");
    await user.type(screen.getByLabelText(/secondary keywords/i), "seo, content");
    await user.click(screen.getByRole("button", { name: /plan article/i }));
    expect(createMutate).toHaveBeenCalledTimes(1);
    const body = createMutate.mock.calls[0][0];
    expect(body.metadata.kind).toBe("article_outline");
    expect(body.metadata.article.topic).toBe("Why founders blog");
    expect(body.metadata.article.secondary_keywords).toEqual(["seo", "content"]);
  });

  it("shows the outline editor when the outline generation completes", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ArticleStudio />);
    const id = await planArticle(user);
    generations[id] = { status: "COMPLETE", result: "## A\n- one\n\n## B\n- two", error_message: null };
    rerender(<ArticleStudio />);
    expect(screen.getByDisplayValue("A")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /write full draft/i })).toBeInTheDocument();
  });

  it("labels the per-section controls with their section number", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ArticleStudio />);
    const id = await planArticle(user);
    generations[id] = { status: "COMPLETE", result: "## A\n- one\n\n## B\n- two", error_message: null };
    rerender(<ArticleStudio />);
    expect(screen.getByRole("button", { name: "Move section 2 up" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Move section 1 down" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remove section 1" })).toBeInTheDocument();
  });

  it("hides the stale outline and draft while the outline regenerates", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ArticleStudio />);
    const outlineId = await planArticle(user);
    generations[outlineId] = { status: "COMPLETE", result: "## A\n- one", error_message: null };
    rerender(<ArticleStudio />);
    expect(screen.getByDisplayValue("A")).toBeInTheDocument();

    // Draft completes, then the user asks for a fresh outline.
    await user.click(screen.getByRole("button", { name: /write full draft/i }));
    const draftId = `gen-${idSeq}`;
    generations[draftId] = { status: "COMPLETE", result: "# Draft body", error_message: null };
    rerender(<ArticleStudio />);
    expect(screen.getByText("# Draft body")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /2 · outline/i }));
    await user.click(screen.getByRole("button", { name: /regenerate outline/i }));

    // The new generation (gen-3) has no data yet: old sections and the old
    // draft must disappear, leaving only the progress note.
    expect(screen.getByText(/planning your outline/i)).toBeInTheDocument();
    expect(screen.queryByDisplayValue("A")).not.toBeInTheDocument();

    // The draft state was really reset: the draft tab is no longer clickable.
    await user.click(screen.getByRole("button", { name: /3 · draft/i }));
    expect(screen.queryByText("# Draft body")).not.toBeInTheDocument();
    expect(screen.getByText(/planning your outline/i)).toBeInTheDocument();
  });

  it("restores the previous outline when a regeneration fails to start", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ArticleStudio />);
    const id = await planArticle(user);
    generations[id] = { status: "COMPLETE", result: "## A\n- one", error_message: null };
    rerender(<ArticleStudio />);
    expect(screen.getByDisplayValue("A")).toBeInTheDocument();

    failNextCreate = true;
    await user.click(screen.getByRole("button", { name: /regenerate outline/i }));

    // The failed start must not destroy the user's edited outline.
    expect(screen.getByDisplayValue("A")).toBeInTheDocument();
    expect(screen.queryByText(/planning your outline/i)).not.toBeInTheDocument();
  });

  it("sends kind=article_draft with the edited outline", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ArticleStudio />);
    const id = await planArticle(user);
    generations[id] = { status: "COMPLETE", result: "## A\n- one", error_message: null };
    rerender(<ArticleStudio />);
    await user.click(screen.getByRole("button", { name: /write full draft/i }));
    const body = createMutate.mock.calls.at(-1)![0];
    expect(body.metadata.kind).toBe("article_draft");
    expect(body.metadata.outline[0].heading).toBe("A");
    // Lineage travels as a first-class field, not a metadata key.
    expect(body.parent_generation_id).toBe(id);
    expect(body.metadata.parent_generation_id).toBeUndefined();
  });

  it("surfaces a generation failure", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ArticleStudio />);
    const id = await planArticle(user);
    generations[id] = { status: "FAILED", result: null, error_message: "model exploded" };
    rerender(<ArticleStudio />);
    expect(screen.getByText(/model exploded/i)).toBeInTheDocument();
    // With no sections there is nothing to draft from.
    expect(screen.getByRole("button", { name: /write full draft/i })).toBeDisabled();
  });
});
