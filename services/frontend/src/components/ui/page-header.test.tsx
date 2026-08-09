import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageHeader } from "./page-header";

function StubIcon({ className }: { className?: string }) {
  return <svg data-testid="stub-icon" className={className} />;
}

describe("PageHeader", () => {
  it("renders the title as the single canonical size (text-3xl h1)", () => {
    render(<PageHeader icon={StubIcon} title="Analytics" />);
    const h1 = screen.getByRole("heading", { level: 1, name: "Analytics" });
    // The whole point of the shared header: one title size platform-wide.
    expect(h1).toHaveClass("text-3xl");
    expect(h1).not.toHaveClass("text-4xl");
  });

  it("always renders a leading icon tile", () => {
    render(<PageHeader icon={StubIcon} title="Library" />);
    const icon = screen.getByTestId("stub-icon");
    expect(icon).toBeInTheDocument();
    // Icon sizing is owned by the header, not the caller.
    expect(icon).toHaveClass("h-6", "w-6");
  });

  it("renders optional eyebrow, subtitle, and actions when provided", () => {
    render(
      <PageHeader
        icon={StubIcon}
        eyebrow="/demo"
        title="Dashboard"
        subtitle="Your workspace at a glance."
        actions={<button>New brand</button>}
      />,
    );
    expect(screen.getByText("/demo")).toBeInTheDocument();
    expect(screen.getByText("Your workspace at a glance.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New brand" })).toBeInTheDocument();
  });

  it("omits eyebrow and subtitle when not provided", () => {
    render(<PageHeader icon={StubIcon} title="Settings" />);
    expect(screen.getByRole("heading", { level: 1, name: "Settings" })).toBeInTheDocument();
    // Only the title text should be present in the header text nodes.
    expect(screen.queryByText("/demo")).not.toBeInTheDocument();
  });
});
