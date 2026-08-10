"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/data-display";
import { useCreateCheckout, useCreatePortalSession, useSubscription } from "../hooks";

const PLAN_LABELS: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  team: "Team",
};

export function BillingCard() {
  const { data: sub, isLoading } = useSubscription();
  const checkout = useCreateCheckout();
  const portal = useCreatePortalSession();
  const [error, setError] = useState<string | null>(null);

  const plan = sub?.billing_plan ?? "free";
  const isPaid = plan !== "free";

  function upgrade(target: "pro" | "team") {
    setError(null);
    checkout.mutate(target, {
      onSuccess: (result) => {
        window.location.href = result.checkout_url;
      },
      onError: (e) => setError(e instanceof Error ? e.message : "Checkout failed"),
    });
  }

  function manage() {
    setError(null);
    portal.mutate(undefined, {
      onSuccess: (result) => {
        window.location.href = result.portal_url;
      },
      onError: (e) => setError(e instanceof Error ? e.message : "Could not open billing portal"),
    });
  }

  return (
    <section className="rounded-[var(--radius-lg)] border border-gray-200 bg-white p-5 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-black text-gray-900">Billing</h2>
          <p className="mt-1 text-xs font-medium text-gray-500">
            Manage your OpenGrow plan and payment method.
          </p>
        </div>
        <Badge tone={isPaid ? "gradient" : "neutral"}>
          {(PLAN_LABELS[plan] ?? plan).toUpperCase()}
        </Badge>
      </div>

      {isLoading && !sub && (
        <p className="mt-4 text-xs font-medium text-gray-400">Loading plan…</p>
      )}

      {sub?.cancel_at_period_end && (
        <p className="mt-4 rounded-xl border border-amber-100 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-700">
          Your subscription is set to cancel at the end of the current billing period.
        </p>
      )}

      {error && (
        <p className="mt-4 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
          {error}
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {isPaid ? (
          <Button onClick={manage} loading={portal.isPending}>
            Manage subscription
          </Button>
        ) : (
          <>
            <Button onClick={() => upgrade("pro")} loading={checkout.isPending}>
              Upgrade to Pro
            </Button>
            <Button
              variant="secondary"
              onClick={() => upgrade("team")}
              loading={checkout.isPending}
            >
              Upgrade to Team
            </Button>
          </>
        )}
      </div>
    </section>
  );
}
