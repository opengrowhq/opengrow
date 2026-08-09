"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { AppShell } from "@/components/ui/app-shell";
import { PageHeader } from "@/components/ui/page-header";
import { StatusPill } from "@/components/ui/status-pill";
import { StatCard } from "@/components/ui/data-display";
import { ButtonLink } from "@/components/ui/button";
import { HomeIcon } from "@/components/illustrations";
import { useAuthGuard, useMe } from "@/features/auth";
import { useBrands } from "@/features/brand";
import { appPath, appRootPath } from "@/lib/app-routes.mjs";
import { firstPaintLoading } from "@/lib/first-paint.mjs";
import { useMounted } from "@/lib/use-mounted";
import {
  type ContentPiece,
  useContentList,
  useCreateContent,
} from "@/features/content";

const filters = ["ALL", "DRAFT", "IN_REVIEW", "APPROVED", "PUBLISHED"];

function toSlug(value: string): string {
  return (
    value
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "untitled"
  );
}

function pagePath(item: ContentPiece): string {
  return `/${toSlug(item.title)}`;
}

function byUpdatedAt(a: ContentPiece, b: ContentPiece): number {
  return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
}

export function SlugsDashboard() {
  const hasToken = useAuthGuard();
  const mounted = useMounted();
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const { data: me } = useMe(hasToken);
  const { data: brands } = useBrands();
  const { data: items, isLoading, error } = useContentList();
  const create = useCreateContent();

  const [title, setTitle] = useState("");
  const [intent, setIntent] = useState("launch");
  const [filter, setFilter] = useState("ALL");

  const tenantSlug = me?.tenant_slug ?? params.slug;
  const showLoading = firstPaintLoading(mounted, isLoading);
  const pages = useMemo(
    () =>
      (items ?? [])
        .filter((item) => item.format === "landing_page" || item.format === "page")
        .sort(byUpdatedAt),
    [items],
  );
  const visible = filter === "ALL" ? pages : pages.filter((p) => p.status === filter);
  const drafts = pages.filter((p) => p.status === "DRAFT").length;
  const approved = pages.filter((p) => p.status === "APPROVED").length;
  const published = pages.filter((p) => p.status === "PUBLISHED").length;

  function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    const cleanTitle = title.trim();
    create.mutate(
      {
        title: cleanTitle,
        format: "landing_page",
        body: [
          `# ${cleanTitle}`,
          "",
          `Intent: ${intent}`,
          "",
          "## Hero",
          "Write the promise, audience, and primary call to action here.",
          "",
          "## Proof",
          "Add outcomes, examples, testimonials, or data.",
          "",
          "## Offer",
          "Describe what the visitor gets and why now.",
        ].join("\n"),
      },
      {
        onSuccess: (cp) => {
          setTitle("");
          router.push(appPath(tenantSlug, "content", cp.id));
        },
      },
    );
  }

  return (
    <AppShell>
      <section>
        <PageHeader
          icon={HomeIcon}
          eyebrow={`/${tenantSlug}`}
          title="Dashboard"
          actions={
            <>
              <ButtonLink href={appPath(tenantSlug, "brand")} variant="secondary" size="sm">
                Brand DNA
              </ButtonLink>
              <ButtonLink href={appPath(tenantSlug, "content")} variant="secondary" size="sm">
                Library
              </ButtonLink>
            </>
          }
        />

        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <Metric label="Pages" value={pages.length} />
          <Metric label="Drafts" value={drafts} />
          <Metric label="Approved" value={approved} />
          <Metric label="Published" value={published} />
        </div>

        <Link
          href={appPath(tenantSlug, "analytics")}
          className="mt-6 flex items-center justify-between gap-4 rounded-[28px] border border-gray-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
        >
          <div>
            <h2 className="text-lg font-semibold">View analytics →</h2>
            <p className="mt-1 text-sm text-gray-500">
              Attribution, channels, sources, tracking, and connectors in a dedicated workspace.
            </p>
          </div>
          <span className="shrink-0 text-sm font-semibold text-interactive">Open workspace</span>
        </Link>

        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <section className="rounded-[28px] border border-gray-200 bg-white p-4 shadow-[0_18px_60px_rgba(15,23,42,0.08)]">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Page slugs</h2>
                <p className="mt-1 text-sm text-gray-500">
                  Landing pages and campaign pages owned by this workspace.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {filters.map((item) => (
                  <button
                    key={item}
                    onClick={() => setFilter(item)}
                    className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                      filter === item
                        ? "bg-interactive text-white"
                        : "border border-gray-200 text-gray-500 hover:bg-gray-50"
                    }`}
                  >
                    {item.replace("_", " ")}
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <p className="mt-4 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error instanceof Error ? error.message : "Failed to load pages"}
              </p>
            )}

            <div className="mt-5 space-y-3">
              {showLoading && (
                <div className="rounded-3xl border border-gray-200 bg-gray-50 py-14 text-center text-sm text-gray-500">
                  Loading...
                </div>
              )}
              {!showLoading && visible.length === 0 && (
                <div className="rounded-3xl border border-dashed border-gray-200 bg-gray-50 py-14 text-center">
                  <p className="text-sm font-semibold text-gray-700">
                    No pages in this view.
                  </p>
                  <p className="mt-1 text-sm text-gray-500">
                    Create a landing page from the panel on the right.
                  </p>
                </div>
              )}
              {!showLoading && visible.map((item) => (
                <Link
                  key={item.id}
                  href={appPath(tenantSlug, "content", item.id)}
                  className="grid gap-4 rounded-3xl border border-gray-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md md:grid-cols-[minmax(0,1fr)_150px_120px]"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-3">
                      <h3 className="truncate text-base font-semibold text-gray-950">
                        {item.title}
                      </h3>
                      <StatusPill status={item.status} />
                    </div>
                    <p className="mt-2 truncate text-sm text-gray-500">
                      {pagePath(item)}
                    </p>
                  </div>
                  <div className="text-sm text-gray-500">
                    Updated
                    <br />
                    <span className="font-semibold text-gray-800">
                      {new Date(item.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="text-sm font-semibold text-interactive">
                    Edit page →
                  </div>
                </Link>
              ))}
            </div>
          </section>

          <aside className="space-y-4">
            <section className="rounded-[28px] border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-lg font-semibold">Create page</h2>
              <form onSubmit={onCreate} className="mt-4 space-y-3">
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Page name"
                  className="w-full rounded-full border border-gray-500 px-4 py-3 text-sm outline-none focus:border-gray-700"
                />
                <select
                  value={intent}
                  onChange={(e) => setIntent(e.target.value)}
                  className="w-full rounded-full border border-gray-500 bg-white px-4 py-3 text-sm outline-none focus:border-gray-700"
                >
                  <option value="launch">Launch</option>
                  <option value="lead_capture">Lead capture</option>
                  <option value="comparison">Comparison</option>
                  <option value="offer">Offer</option>
                </select>
                <button
                  type="submit"
                  disabled={create.isPending || !title.trim()}
                  className="h-11 w-full rounded-full bg-interactive text-sm font-semibold text-white shadow-sm hover:bg-interactive-hover disabled:opacity-50"
                >
                  Create slug
                </button>
              </form>
            </section>

            <section className="rounded-[28px] border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-lg font-semibold">Setup</h2>
              <div className="mt-4 space-y-3 text-sm">
                <SetupRow
                  label="Brand DNA"
                  done={!!brands?.length}
                  href={appPath(tenantSlug, "brand")}
                />
                <SetupRow label="Create first slug" done={pages.length > 0} href={appRootPath(tenantSlug)} />
                <SetupRow
                  label="Approve content"
                  done={approved + published > 0}
                  href={appPath(tenantSlug, "content")}
                />
                <SetupRow label="Publish PR" done={published > 0} href={appPath(tenantSlug, "content")} />
              </div>
            </section>
          </aside>
        </div>
      </section>
    </AppShell>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return <StatCard label={label} value={value} />;
}

function SetupRow({
  label,
  done,
  href,
}: {
  label: string;
  done: boolean;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-center justify-between rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 font-semibold text-gray-700"
    >
      {label}
      <span className={done ? "text-emerald-500" : "text-gray-300"}>
        {done ? "✓" : "○"}
      </span>
    </Link>
  );
}
