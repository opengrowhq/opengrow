import { apiGet, apiSend } from "@/lib/http";

export type CheckoutResult = { checkout_url: string };
export type PortalResult = { portal_url: string };
export type Subscription = {
  billing_plan: string;
  subscription_status: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
};

export const getSubscription = () => apiGet<Subscription>("/billing/subscription");

export const createCheckout = (plan: "pro" | "team") =>
  apiSend<CheckoutResult>("/billing/checkout", "POST", { plan });

export const createPortalSession = () =>
  apiSend<PortalResult>("/billing/portal", "POST", {});

export const createTopupCheckout = (amountEurCents: number) =>
  apiSend<CheckoutResult>("/billing/topup", "POST", {
    amount_eur_cents: amountEurCents,
  });
