import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    getSubscription: vi.fn(),
    createCheckout: vi.fn(),
    createPortalSession: vi.fn(),
    createTopupCheckout: vi.fn(),
  };
});

import {
  getSubscription,
  createCheckout,
  createPortalSession,
  createTopupCheckout,
} from "../api";
import { BillingCard } from "./billing-card";

const getSubscriptionMock = vi.mocked(getSubscription);
const createCheckoutMock = vi.mocked(createCheckout);
const createPortalSessionMock = vi.mocked(createPortalSession);
const createTopupCheckoutMock = vi.mocked(createTopupCheckout);

const freePlan = {
  billing_plan: "free",
  subscription_status: null,
  current_period_end: null,
  cancel_at_period_end: false,
};
const proPlan = {
  billing_plan: "pro",
  subscription_status: "ACTIVE",
  current_period_end: "2026-09-01T00:00:00Z",
  cancel_at_period_end: false,
};
const pastDuePlan = {
  billing_plan: "pro",
  subscription_status: "PAST_DUE",
  current_period_end: "2026-09-01T00:00:00Z",
  cancel_at_period_end: false,
};

function renderCard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <BillingCard />
    </QueryClientProvider>,
  );
}

const originalLocation = window.location;

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.setItem("opengrow.token", "test-token");
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { ...originalLocation, href: "" },
  });
});

describe("BillingCard", () => {
  it("shows Free plan and upgrade buttons when unsubscribed", async () => {
    getSubscriptionMock.mockResolvedValue(freePlan);
    renderCard();
    expect(await screen.findByText("FREE")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upgrade to Pro" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upgrade to Team" })).toBeInTheDocument();
  });

  it("shows the plan badge and manage button when subscribed", async () => {
    getSubscriptionMock.mockResolvedValue(proPlan);
    renderCard();
    expect(await screen.findByText("PRO")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Manage subscription" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Upgrade to Pro" })).not.toBeInTheDocument();
  });

  it("shows a cancellation notice when cancel_at_period_end is set", async () => {
    getSubscriptionMock.mockResolvedValue({ ...proPlan, cancel_at_period_end: true });
    renderCard();
    expect(
      await screen.findByText(/set to cancel at the end of the current billing period/),
    ).toBeInTheDocument();
  });

  it("shows a past-due warning for a past-due plan", async () => {
    getSubscriptionMock.mockResolvedValue(pastDuePlan);
    renderCard();
    expect(await screen.findByText(/Your last payment failed/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Update payment method" }),
    ).toBeInTheDocument();
  });

  it("does not show the past-due warning for an active plan", async () => {
    getSubscriptionMock.mockResolvedValue(proPlan);
    renderCard();
    expect(await screen.findByText("PRO")).toBeInTheDocument();
    expect(screen.queryByText(/Your last payment failed/)).not.toBeInTheDocument();
  });

  it("redirects to the Billing Portal from the past-due warning", async () => {
    const user = userEvent.setup();
    getSubscriptionMock.mockResolvedValue(pastDuePlan);
    createPortalSessionMock.mockResolvedValue({ portal_url: "https://stripe.test/portal/2" });
    renderCard();

    await user.click(await screen.findByRole("button", { name: "Update payment method" }));

    await waitFor(() => {
      expect(createPortalSessionMock).toHaveBeenCalled();
      expect(window.location.href).toBe("https://stripe.test/portal/2");
    });
  });

  it("redirects to the Checkout URL on upgrade", async () => {
    const user = userEvent.setup();
    getSubscriptionMock.mockResolvedValue(freePlan);
    createCheckoutMock.mockResolvedValue({ checkout_url: "https://stripe.test/checkout/1" });
    renderCard();

    await user.click(await screen.findByRole("button", { name: "Upgrade to Pro" }));

    await waitFor(() => {
      expect(createCheckoutMock.mock.calls[0]?.[0]).toBe("pro");
      expect(window.location.href).toBe("https://stripe.test/checkout/1");
    });
  });

  it("redirects to the Billing Portal URL on manage", async () => {
    const user = userEvent.setup();
    getSubscriptionMock.mockResolvedValue(proPlan);
    createPortalSessionMock.mockResolvedValue({ portal_url: "https://stripe.test/portal/1" });
    renderCard();

    await user.click(await screen.findByRole("button", { name: "Manage subscription" }));

    await waitFor(() => {
      expect(createPortalSessionMock).toHaveBeenCalled();
      expect(window.location.href).toBe("https://stripe.test/portal/1");
    });
  });

  it("shows credit top-up buttons only for a paid plan", async () => {
    getSubscriptionMock.mockResolvedValue(freePlan);
    renderCard();
    expect(await screen.findByText("FREE")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /credit/ })).not.toBeInTheDocument();
  });

  it("redirects to the top-up Checkout URL when a tier is bought", async () => {
    const user = userEvent.setup();
    getSubscriptionMock.mockResolvedValue(proPlan);
    createTopupCheckoutMock.mockResolvedValue({
      checkout_url: "https://stripe.test/checkout/topup",
    });
    renderCard();

    await user.click(await screen.findByRole("button", { name: "+€25 credit" }));

    await waitFor(() => {
      expect(createTopupCheckoutMock.mock.calls[0]?.[0]).toBe(2_500);
      expect(window.location.href).toBe("https://stripe.test/checkout/topup");
    });
  });
});
