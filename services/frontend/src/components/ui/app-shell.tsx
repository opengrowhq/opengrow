"use client";

import { type ComponentType, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { useHasToken, useMe } from "@/features/auth";
import { appPath, appRootPath } from "@/lib/app-routes.mjs";
import { clearToken } from "@/lib/auth";
import {
  AdIcon,
  ArticleIcon,
  BrandIcon,
  BrandMark,
  CalendarIcon,
  ChartIcon,
  EmailIcon,
  HomeIcon,
  LibraryIcon,
  SettingsIcon,
  SocialIcon,
  SparkIcon,
} from "@/components/illustrations";
import { Drawer } from "@/components/ui/overlay";

type IconType = ComponentType<{ className?: string }>;

const NAV: { seg: string; label: string; icon: IconType }[] = [
  { seg: "__home__", label: "Home", icon: HomeIcon },
  { seg: "articles", label: "Articles", icon: ArticleIcon },
  { seg: "ads", label: "Ads", icon: AdIcon },
  { seg: "socials", label: "Socials", icon: SocialIcon },
  { seg: "emails", label: "Emails", icon: EmailIcon },
  { seg: "content", label: "Library", icon: LibraryIcon },
  { seg: "analytics", label: "Analytics", icon: ChartIcon },
  { seg: "calendar", label: "Calendar", icon: CalendarIcon },
  { seg: "brand", label: "Brand DNA", icon: BrandIcon },
  { seg: "settings", label: "Settings", icon: SettingsIcon },
];

function NavList({
  slug,
  pathname,
  onNavigate,
}: {
  slug: string | undefined;
  pathname: string;
  onNavigate?: () => void;
}) {
  const homeHref = appRootPath(slug);
  return (
    <nav className="space-y-1">
      {NAV.map((item) => {
        const href = item.seg === "__home__" ? homeHref : appPath(slug, item.seg);
        const active =
          item.seg === "__home__"
            ? pathname === href
            : pathname === href || pathname.startsWith(`${href}/`);
        const Icon = item.icon;
        return (
          <Link
            key={item.label}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={`relative flex h-10 items-center gap-3 rounded-full px-3 text-sm font-bold transition-colors ${
              active ? "text-gray-950" : "text-gray-500 hover:text-gray-900"
            }`}
          >
            {active && (
              <motion.span
                layoutId="app-nav-active"
                className="absolute inset-0 rounded-full bg-gray-100"
                transition={{ type: "spring", stiffness: 400, damping: 32 }}
              />
            )}
            <Icon className="relative h-[18px] w-[18px]" />
            <span className="relative">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function UserButton({
  email,
  onAddBrand,
  onSignOut,
}: {
  email: string | undefined;
  onAddBrand: () => void;
  onSignOut: () => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative mt-auto">
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.98 }}
            transition={{ duration: 0.18 }}
            className="absolute bottom-14 left-0 right-0 rounded-2xl border border-gray-200 bg-white p-3 shadow-lift"
          >
            <p className="text-sm font-black">OpenGrow</p>
            <p className="truncate text-xs text-gray-500">{email ?? "Demo user"}</p>
            <button
              onClick={() => {
                setOpen(false);
                onAddBrand();
              }}
              className="mt-4 flex w-full items-center gap-2 rounded-lg px-1 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-950"
            >
              <span className="text-lg">+</span> Add new brand
            </button>
            <button
              onClick={() => {
                setOpen(false);
                onSignOut();
              }}
              className="mt-1 flex w-full items-center gap-2 rounded-lg px-1 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-950"
            >
              <span>↪</span> Sign out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex h-12 w-full items-center gap-2 rounded-full border border-gray-200 bg-white px-2 text-left shadow-sm transition hover:bg-gray-50"
      >
        <BrandMark className="h-8 w-8" />
        <span className="truncate text-sm font-bold">{email ?? "OpenGrow"}</span>
      </button>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const hasToken = useHasToken();
  const { data: me } = useMe(hasToken);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const tenantSlug = me?.tenant_slug;

  const addBrand = () => router.push(appPath(tenantSlug, "onboarding"));
  const signOut = () => {
    clearToken();
    router.replace("/login");
  };

  return (
    <main className="min-h-screen bg-[var(--app-canvas)] text-gray-950">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 flex-col border-r border-gray-100 bg-white/85 px-4 py-5 backdrop-blur-xl md:flex">
        <Link href={appRootPath(tenantSlug)} className="mb-6 flex items-center gap-2.5 px-1">
          <BrandMark className="h-9 w-9" />
          <span className="text-lg font-black tracking-tight">OpenGrow</span>
        </Link>
        <NavList slug={tenantSlug} pathname={pathname} />
        <div className="mt-7 px-1 text-sm">
          <div className="flex items-center justify-between text-gray-500">
            <span className="text-xs font-bold uppercase tracking-wide">History</span>
            <SparkIcon className="h-4 w-4" />
          </div>
          <p className="mt-2 text-xs text-gray-400">No activity yet.</p>
        </div>
        <UserButton email={me?.email} onAddBrand={addBrand} onSignOut={signOut} />
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-gray-100 bg-white/85 px-4 backdrop-blur-xl md:hidden">
        <Link href={appRootPath(tenantSlug)} className="flex items-center gap-2">
          <BrandMark className="h-8 w-8" />
          <span className="text-base font-black">OpenGrow</span>
        </Link>
        <button
          type="button"
          aria-label="Open menu"
          onClick={() => setDrawerOpen(true)}
          className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-white"
        >
          <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5">
            <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </button>
      </header>

      {/* Mobile drawer */}
      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} side="left" className="flex flex-col p-5">
        <Link
          href={appRootPath(tenantSlug)}
          onClick={() => setDrawerOpen(false)}
          className="mb-6 flex items-center gap-2.5"
        >
          <BrandMark className="h-9 w-9" />
          <span className="text-lg font-black tracking-tight">OpenGrow</span>
        </Link>
        <NavList slug={tenantSlug} pathname={pathname} onNavigate={() => setDrawerOpen(false)} />
        <UserButton email={me?.email} onAddBrand={addBrand} onSignOut={signOut} />
      </Drawer>

      <div className="min-h-screen md:pl-60">
        <div className="min-h-screen border-gray-100 bg-white md:rounded-l-[28px] md:border-l">
          <div className="mx-auto max-w-6xl px-5 py-8 md:px-10">{children}</div>
        </div>
      </div>
    </main>
  );
}
