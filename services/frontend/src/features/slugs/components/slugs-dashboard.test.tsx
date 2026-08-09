import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useParams: () => ({ slug: "demo" }),
  useRouter: () => ({ push }),
}));

// Render the shell as a passthrough so we test the dashboard, not the nav.
vi.mock("@/components/ui/app-shell", () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/features/auth", () => ({
  useAuthGuard: () => true,
  useMe: () => ({ data: { tenant_slug: "demo" } }),
}));
vi.mock("@/features/brand", () => ({ useBrands: () => ({ data: [{ id: "b1" }] }) }));

vi.mock("@/features/content", () => ({
  useContentList: () => ({ data: [], isLoading: false, error: null }),
  useCreateContent: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { SlugsDashboard } from "./slugs-dashboard";

describe("SlugsDashboard", () => {
  beforeEach(() => {
    push.mockClear();
  });

  it("links to the analytics workspace and drops inline attribution", () => {
    render(<SlugsDashboard />);

    const link = screen.getByRole("link", { name: /analytics/i });
    expect(link).toHaveAttribute("href", "/app/demo/analytics");

    expect(screen.queryByRole("heading", { name: /^Revenue funnel$/ })).toBeNull();
    expect(screen.queryByRole("heading", { name: /^Connectors$/ })).toBeNull();
  });
});
