import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "./button";
import { Badge } from "./data-display";

// White label text needs 4.5:1. The brand gradient cannot provide it — measured
// against the shipping Tailwind 4 palette. The brand green #15803D is 5.02:1.
// The gradient survives as decoration (glow shadow, logo, tab underline), just
// never underneath white text.
describe("primary CTA contrast", () => {
  it("fills the primary button with an accessible solid, not the gradient", () => {
    render(<Button>Publish</Button>);
    const btn = screen.getByRole("button", { name: "Publish" });
    expect(btn).toHaveClass("bg-interactive");
    expect(btn).not.toHaveClass("bg-grad");
  });

  it("darkens on hover rather than lightening", () => {
    render(<Button>Publish</Button>);
    expect(screen.getByRole("button", { name: "Publish" })).toHaveClass("hover:bg-interactive-hover");
  });

  it("keeps the other variants unchanged", () => {
    render(
      <>
        <Button variant="danger">Delete</Button>
        <Button variant="ghost">Cancel</Button>
      </>,
    );
    expect(screen.getByRole("button", { name: "Delete" })).toHaveClass("bg-red-600");
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveClass("text-gray-700");
  });

  it("does not put white badge text on the gradient", () => {
    render(<Badge tone="gradient">Live</Badge>);
    const badge = screen.getByText("Live");
    expect(badge).toHaveClass("bg-interactive");
    expect(badge).not.toHaveClass("bg-grad");
  });
});
