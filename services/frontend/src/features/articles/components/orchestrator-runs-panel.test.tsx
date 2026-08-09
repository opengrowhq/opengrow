import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const runFixture = (over: Record<string, unknown> = {}) => ({
  run_id: "run-1",
  status: "AWAITING_OUTLINE_APPROVAL",
  step: "await_outline",
  brief: "Why founders blog",
  generation_id: null,
  content_piece_id: null,
  result: null,
  error_message: null,
  outline: [
    { heading: "Intro", points: ["hook"] },
    { heading: "Body", points: ["point"] },
  ],
  outline_generation_id: "gen-1",
  draft_generation_id: null,
  ...over,
});

let runsData: unknown[] = [];
let runDetail: unknown;
const approveMutate = vi.fn();
const resumeMutate = vi.fn();

vi.mock("../orchestrator-hooks", () => ({
  useOrchestratorRuns: () => ({ data: runsData, isLoading: false }),
  useOrchestratorRun: () => ({ data: runDetail }),
  useApproveOrchestratorOutline: () => ({
    mutate: approveMutate,
    isPending: false,
    error: null,
  }),
  useResumeOrchestratorRun: () => ({ mutate: resumeMutate, isPending: false }),
}));

import { OrchestratorRunsPanel } from "./orchestrator-runs-panel";

beforeEach(() => {
  runsData = [];
  runDetail = undefined;
  approveMutate.mockClear();
  resumeMutate.mockClear();
});

describe("OrchestratorRunsPanel", () => {
  it("shows the empty state without runs", () => {
    render(
      <OrchestratorRunsPanel tenantSlug="demo" selectedRunId={null} onSelectRun={() => {}} />,
    );
    expect(screen.getByText(/no runs yet/i)).toBeInTheDocument();
  });

  it("lists runs with their status badge", () => {
    runsData = [runFixture()];
    render(
      <OrchestratorRunsPanel tenantSlug="demo" selectedRunId={null} onSelectRun={() => {}} />,
    );
    expect(screen.getByText("Why founders blog")).toBeInTheDocument();
    expect(screen.getByText(/awaiting outline approval/i)).toBeInTheDocument();
  });

  it("lets the user edit and approve the outline of an awaiting run", async () => {
    const user = userEvent.setup();
    runsData = [runFixture()];
    runDetail = runFixture();
    render(
      <OrchestratorRunsPanel tenantSlug="demo" selectedRunId="run-1" onSelectRun={() => {}} />,
    );
    const heading = screen.getByLabelText("Section 1 heading");
    await user.clear(heading);
    await user.type(heading, "Better intro");
    await user.click(screen.getByRole("button", { name: /approve outline & write draft/i }));
    expect(approveMutate).toHaveBeenCalledWith({
      id: "run-1",
      outline: [
        { heading: "Better intro", points: ["hook"] },
        { heading: "Body", points: ["point"] },
      ],
    });
  });

  it("shows the error and a resume button on a failed run", async () => {
    const user = userEvent.setup();
    runDetail = runFixture({ status: "FAILED", step: "draft", error_message: "llm down" });
    runsData = [runDetail];
    render(
      <OrchestratorRunsPanel tenantSlug="demo" selectedRunId="run-1" onSelectRun={() => {}} />,
    );
    expect(screen.getByText("llm down")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /resume run/i }));
    expect(resumeMutate).toHaveBeenCalledWith("run-1");
  });

  it("links to the content piece when the run completes", () => {
    runDetail = runFixture({ status: "COMPLETE", step: "done", content_piece_id: "cp-9" });
    runsData = [runDetail];
    render(
      <OrchestratorRunsPanel tenantSlug="demo" selectedRunId="run-1" onSelectRun={() => {}} />,
    );
    expect(
      screen.getByRole("link", { name: /open the content piece/i }),
    ).toHaveAttribute("href", "/app/demo/content/cp-9");
  });
});
