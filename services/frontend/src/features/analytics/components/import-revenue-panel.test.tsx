import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { dollarsToCents } from "../import-form.mjs";

const importMutate = vi.fn();
const revenueMutate = vi.fn();
const importCsvMutate = vi.fn();
vi.mock("../hooks", () => ({
  useImportAnalyticsEvents: () => ({ mutate: importMutate, isPending: false }),
  useCreateRevenueEvent: () => ({ mutate: revenueMutate, isPending: false }),
  useImportAnalyticsEventsCsv: () => ({
    mutate: importCsvMutate,
    isPending: false,
    data: undefined,
    error: null,
  }),
}));
import { ImportRevenuePanel } from "./import-revenue-panel";

function revenueSection() {
  return screen.getByRole("heading", { name: "Revenue event" }).closest("section")!;
}

describe("ImportRevenuePanel", () => {
  beforeEach(() => {
    importMutate.mockClear();
    revenueMutate.mockClear();
    importCsvMutate.mockClear();
  });

  it("renders import and manual revenue forms", () => {
    render(<ImportRevenuePanel />);
    expect(screen.getAllByText(/import/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/revenue/i).length).toBeGreaterThan(0);
  });

  it("submits a revenue event with populated optional fields", async () => {
    const user = userEvent.setup();
    render(<ImportRevenuePanel />);
    const section = revenueSection();

    await user.click(within(section).getByRole("button", { name: "customer" }));
    await user.type(
      within(section).getByPlaceholderText("Content piece ID (optional)"),
      "piece-1",
    );
    await user.type(within(section).getByPlaceholderText("Amount"), "12.50");
    await user.click(within(section).getByRole("button", { name: "Save revenue event" }));

    expect(revenueMutate).toHaveBeenCalledTimes(1);
    expect(revenueMutate.mock.calls[0][0]).toEqual({
      event_type: "customer",
      content_piece_id: "piece-1",
      amount_cents: dollarsToCents("12.50"),
      currency: "USD",
    });
  });

  it("omits blank optional fields, keeping only event_type and defaulted currency", async () => {
    const user = userEvent.setup();
    render(<ImportRevenuePanel />);
    const section = revenueSection();

    await user.type(within(section).getByPlaceholderText("Amount"), "12.50");
    await user.click(within(section).getByRole("button", { name: "Save revenue event" }));

    expect(revenueMutate).toHaveBeenCalledTimes(1);
    expect(revenueMutate.mock.calls[0][0]).toEqual({
      event_type: "revenue",
      amount_cents: dollarsToCents("12.50"),
      currency: "USD",
    });
  });

  it("disables the revenue submit button when only the default event_type is set", () => {
    render(<ImportRevenuePanel />);
    const section = revenueSection();

    expect(
      within(section).getByRole("button", { name: "Save revenue event" }),
    ).toBeDisabled();
  });

  it("enables the revenue submit button once a meaningful field is filled", async () => {
    const user = userEvent.setup();
    render(<ImportRevenuePanel />);
    const section = revenueSection();

    await user.type(within(section).getByPlaceholderText("Amount"), "12.50");

    expect(
      within(section).getByRole("button", { name: "Save revenue event" }),
    ).toBeEnabled();
  });

  it("does not submit when the button is disabled", async () => {
    const user = userEvent.setup();
    render(<ImportRevenuePanel />);
    const section = revenueSection();

    await user.click(within(section).getByRole("button", { name: "Save revenue event" }));

    expect(revenueMutate).not.toHaveBeenCalled();
  });

  it("uploads a selected CSV file with the currently selected provider", async () => {
    const user = userEvent.setup();
    render(<ImportRevenuePanel />);

    const file = new File(["visits\n5\n"], "import.csv", { type: "text/csv" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    expect(importCsvMutate).toHaveBeenCalledTimes(1);
    const [args] = importCsvMutate.mock.calls[0];
    expect(args.file).toBe(file);
    expect(args.provider).toBe("manual");
  });
});
