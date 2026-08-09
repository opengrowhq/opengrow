import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Field, Input, Select, Textarea, controlClass } from "./field";

// These assertions pin WCAG minimums, not aesthetics. Measured against the
// shipping Tailwind 4 palette (OKLCH) on white (#fff) and the app canvas
// (#F5F7FA):
//   gray-300 #D1D5DC = 1.47:1  -> fails the 3:1 control-boundary minimum
//   gray-400 #99A1AF = 2.60:1  -> fails the 4.5:1 text minimum
//   gray-500 #6A7282 = 4.84:1 on white / 4.51:1 on canvas -> clears both
describe("form control accessibility", () => {
  it("gives inputs a boundary that clears the 3:1 non-text minimum", () => {
    render(<Input placeholder="Repo" />);
    const input = screen.getByPlaceholderText("Repo");
    expect(input).toHaveClass("border-gray-500");
    expect(input).not.toHaveClass("border-gray-300");
  });

  it("gives placeholders a colour that clears the 4.5:1 text minimum", () => {
    render(<Input placeholder="Repo" />);
    const input = screen.getByPlaceholderText("Repo");
    expect(input).toHaveClass("placeholder:text-gray-500");
    expect(input).not.toHaveClass("placeholder:text-gray-400");
  });

  it("applies the same accessible control style to Textarea and Select", () => {
    render(
      <>
        <Textarea placeholder="Body" />
        <Select aria-label="Channel">
          <option>One</option>
        </Select>
      </>,
    );
    for (const el of [screen.getByPlaceholderText("Body"), screen.getByLabelText("Channel")]) {
      expect(el).toHaveClass("border-gray-500");
      expect(el).toHaveClass("placeholder:text-gray-500");
    }
  });

  it("renders hint text at a readable contrast", () => {
    render(
      <Field label="Repo" hint="owner/name">
        <Input />
      </Field>,
    );
    const hint = screen.getByText("owner/name");
    expect(hint).toHaveClass("text-gray-500");
    expect(hint).not.toHaveClass("text-gray-400");
  });

  it("carries the accessible values through every controlClass variant", () => {
    // The three feature surfaces vary only in padding / disabled treatment;
    // the accessibility-critical classes must survive every variant.
    for (const cls of [
      controlClass(),
      controlClass("py-2.5 disabled:opacity-60"),
      controlClass("py-3"),
    ]) {
      expect(cls).toContain("border-gray-500");
      expect(cls).toContain("placeholder:text-gray-500");
      expect(cls).not.toContain("border-gray-300");
      expect(cls).not.toContain("placeholder:text-gray-400");
    }
  });

  it("does not bake padding into the base, so callers cannot collide", () => {
    // Appending a conflicting utility would not reliably win: Tailwind
    // precedence comes from stylesheet order, not className order.
    expect(controlClass("py-2.5 disabled:opacity-60")).not.toContain("py-3");
  });

  it("keeps a visible label rather than relying on the placeholder", () => {
    render(
      <Field label="Repo" htmlFor="repo">
        <Input id="repo" placeholder="owner/name" />
      </Field>,
    );
    expect(screen.getByText("Repo")).toBeInTheDocument();
    expect(screen.getByLabelText("Repo")).toBe(screen.getByPlaceholderText("owner/name"));
  });
});
