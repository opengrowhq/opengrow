"use client";

import { AppShell } from "@/components/ui/app-shell";
import { PageHeader } from "@/components/ui/page-header";
import { SettingsIcon } from "@/components/illustrations";
import { useAuthGuard } from "@/features/auth";
import { BillingCard } from "@/features/billing";
import { GitHubConnectionCard } from "./github-connection-card";

export function SettingsPage() {
  useAuthGuard();

  return (
    <AppShell>
      <main className="space-y-6">
        <PageHeader
          icon={SettingsIcon}
          title="Settings"
          subtitle="Workspace integrations and publishing connections."
        />
        <BillingCard />
        <GitHubConnectionCard />
      </main>
    </AppShell>
  );
}
