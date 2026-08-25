import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@/components/ui/app-shell", () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/features/auth", () => ({ useAuthGuard: () => true, useMe: () => ({ data: { tenant_slug: "demo" } }) }));
const summaryFixture = {
  events: 42,
  visits: 100,
  signups: 20,
  leads: 15,
  customers: 8,
  revenue_cents: 123456,
  currency: "USD",
};

let summaryHookResult: {
  data: typeof summaryFixture | undefined;
  isLoading: boolean;
  isError?: boolean;
  error?: unknown;
} = { data: summaryFixture, isLoading: false };

let trendsData: {
  content?: unknown[];
  channels?: unknown[];
  sources?: unknown[];
} = {};

vi.mock("../hooks", () => ({
  useAttributionSummary: () => summaryHookResult,
  useAttributionTrend: () => ({ data: undefined, isLoading: false, error: undefined }),
  useContentAttribution: () => ({ data: undefined, isLoading: false, error: undefined }),
  useSourceAttribution: () => ({ data: undefined, isLoading: false, error: undefined }),
  useChannelAttribution: () => ({ data: undefined, isLoading: false, error: undefined }),
  useContentTrends: () => ({ data: trendsData.content }),
  useChannelTrends: () => ({ data: trendsData.channels }),
  useSourceTrends: () => ({ data: trendsData.sources }),
  useTrackingStatus: () => ({ data: undefined }),
  useAnalyticsConnectors: () => ({ data: [] }),
  useCreateAnalyticsConnector: () => ({ mutate: vi.fn(), isPending: false }),
  useDisconnectAnalyticsConnector: () => ({ mutate: vi.fn(), isPending: false }),
  useGoogleAuthUrl: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useCompleteGoogleConnectorOAuth: () => ({ mutate: vi.fn(), isPending: false }),
  useSyncAnalyticsConnector: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateRevenueEvent: () => ({ mutate: vi.fn(), isPending: false }),
  useImportAnalyticsEvents: () => ({ mutate: vi.fn(), isPending: false }),
  useImportAnalyticsEventsCsv: () => ({ mutate: vi.fn(), isPending: false }),
  useRecommendations: () => ({ data: [], isLoading: false, error: undefined }),
  useDismissRecommendation: () => ({ mutate: vi.fn(), isPending: false, isError: false }),
  useStartRunFromRecommendation: () => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  }),
}));

import { AnalyticsDashboard } from "./analytics-dashboard";

describe("AnalyticsDashboard", () => {
  beforeEach(() => {
    summaryHookResult = { data: summaryFixture, isLoading: false };
    trendsData = {};
  });

  it("renders the analytics heading", () => {
    render(<AnalyticsDashboard />);
    expect(screen.getByRole("heading", { name: /analytics/i })).toBeInTheDocument();
  });

  it("renders window selector and breakdown tabs", () => {
    render(<AnalyticsDashboard />);
    expect(screen.getByText("30d")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Content" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Channels" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sources" })).toBeInTheDocument();
  });

  it("renders a loading affordance while the summary is loading, not the empty state", () => {
    summaryHookResult = { data: undefined, isLoading: true };
    render(<AnalyticsDashboard />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(screen.queryByText("No attribution data yet")).not.toBeInTheDocument();
  });

  it("renders an error affordance when the summary query errors, not the empty state", () => {
    summaryHookResult = {
      data: undefined,
      isLoading: false,
      isError: true,
      error: { message: "network down" },
    };
    render(<AnalyticsDashboard />);
    expect(screen.getByText("Couldn't load analytics")).toBeInTheDocument();
    expect(screen.queryByText("No attribution data yet")).not.toBeInTheDocument();
  });

  const trendShape = {
    current: {
      events: 5,
      visits: 10,
      signups: 2,
      leads: 3,
      customers: 1,
      revenue_cents: 100,
      currency: "USD",
    },
    previous: {
      events: 2,
      visits: 4,
      signups: 1,
      leads: 1,
      customers: 0,
      revenue_cents: 0,
      currency: "USD",
    },
    deltas: {},
  };

  it("renders content trend cards linking to the content piece", () => {
    trendsData = {
      content: [
        { content_piece_id: "cp1", title: "Compounding post", status: "PUBLISHED", ...trendShape },
      ],
    };
    render(<AnalyticsDashboard />);
    const link = screen.getByRole("link", { name: "Compounding post" });
    expect(link).toHaveAttribute("href", "/app/demo/content/cp1");
  });

  it("renders channel trend cards on the channels tab", async () => {
    const user = userEvent.setup();
    trendsData = { channels: [{ channel: "google", ...trendShape }] };
    render(<AnalyticsDashboard />);
    await user.click(screen.getByRole("button", { name: "Channels" }));
    expect(screen.getByText("google")).toBeInTheDocument();
  });

  it("renders source trend cards on the sources tab", async () => {
    const user = userEvent.setup();
    trendsData = { sources: [{ source_url: "https://x.com/post", ...trendShape }] };
    render(<AnalyticsDashboard />);
    await user.click(screen.getByRole("button", { name: "Sources" }));
    expect(screen.getByText("https://x.com/post")).toBeInTheDocument();
  });
});
