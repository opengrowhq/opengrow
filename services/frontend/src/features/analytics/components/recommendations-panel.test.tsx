import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

type Recommendation = {
  id: string;
  kind: "REFRESH" | "DOUBLE_DOWN" | "NEW_TOPIC";
  content_piece_id: string | null;
  title: string;
  rationale: string;
  score: number;
  status: string;
  orchestrator_run_id: string | null;
  created_at: string;
};

const recFixture = (over: Partial<Recommendation> = {}): Recommendation => ({
  id: "r1",
  kind: "REFRESH",
  content_piece_id: "cp1",
  title: 'Refresh "Old post"',
  rationale: "traffic dropped 80%",
  score: 0.8,
  status: "PENDING",
  orchestrator_run_id: null,
  created_at: "",
  ...over,
});

let recommendationsData: Recommendation[] = [];
let isLoading = false;
let queryError: unknown = null;

const dismissMutate = vi.fn();
const startRunMutate = vi.fn();

vi.mock("../hooks", () => ({
  useRecommendations: () => ({
    data: recommendationsData,
    isLoading,
    error: queryError,
  }),
  useDismissRecommendation: () => ({
    mutate: dismissMutate,
    isPending: false,
    isError: false,
    error: null,
  }),
  useStartRunFromRecommendation: () => ({
    mutate: startRunMutate,
    isPending: false,
    isError: false,
    error: null,
  }),
}));

import { RecommendationsPanel } from "./recommendations-panel";

beforeEach(() => {
  recommendationsData = [recFixture()];
  isLoading = false;
  queryError = null;
  dismissMutate.mockClear();
  startRunMutate.mockClear();
});

describe("RecommendationsPanel", () => {
  it("lists pending recommendations with kind, title, and rationale", () => {
    render(<RecommendationsPanel />);
    expect(screen.getByText("Refresh")).toBeInTheDocument();
    expect(screen.getByText('Refresh "Old post"')).toBeInTheDocument();
    expect(screen.getByText("traffic dropped 80%")).toBeInTheDocument();
  });

  it("shows a loading affordance", () => {
    isLoading = true;
    recommendationsData = [];
    render(<RecommendationsPanel />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows an error affordance", () => {
    queryError = new Error("network down");
    recommendationsData = [];
    render(<RecommendationsPanel />);
    expect(screen.getByText(/couldn.t load recommendations/i)).toBeInTheDocument();
  });

  it("shows an empty state when there are no recommendations", () => {
    recommendationsData = [];
    render(<RecommendationsPanel />);
    expect(screen.getByText(/no recommendations yet/i)).toBeInTheDocument();
  });

  it("dismisses a recommendation by id", async () => {
    const user = userEvent.setup();
    render(<RecommendationsPanel />);
    await user.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(dismissMutate).toHaveBeenCalledWith("r1");
  });

  it("starts a run from a recommendation by id", async () => {
    const user = userEvent.setup();
    render(<RecommendationsPanel />);
    await user.click(screen.getByRole("button", { name: "Start run" }));
    expect(startRunMutate).toHaveBeenCalledWith("r1");
  });

  it("renders a NEW_TOPIC recommendation without a linked content piece", () => {
    recommendationsData = [
      recFixture({
        id: "r2",
        kind: "NEW_TOPIC",
        content_piece_id: null,
        title: 'Write more on "pricing"',
        rationale: "No published content covers this yet",
      }),
    ];
    render(<RecommendationsPanel />);
    expect(screen.getByText("New topic")).toBeInTheDocument();
    expect(screen.getByText('Write more on "pricing"')).toBeInTheDocument();
  });
});
