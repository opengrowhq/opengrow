// Original inline SVG illustrations & icons — self-contained (no external assets),
// so they satisfy the CSP/offline constraint. Each accepts a className.

type IconProps = { className?: string };

const GRAD_STOPS = (
  <>
    <stop offset="0%" stopColor="#0B3B2E" />
    <stop offset="50%" stopColor="#15803D" />
    <stop offset="100%" stopColor="#16A34A" />
  </>
);

/* --------------------------------- Channel icons --------------------------------- */

export function AdIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <rect x="3" y="5" width="18" height="14" rx="3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M7 15l3-4 2.5 3L15 11l2 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="9" cy="9" r="1.4" fill="currentColor" />
    </svg>
  );
}

export function SocialIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path d="M21 11.5a8.5 8.5 0 01-12.4 7.55L4 20l1-4.5A8.5 8.5 0 1121 11.5z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <circle cx="9" cy="11.5" r="1.1" fill="currentColor" />
      <circle cx="12.5" cy="11.5" r="1.1" fill="currentColor" />
      <circle cx="16" cy="11.5" r="1.1" fill="currentColor" />
    </svg>
  );
}

export function EmailIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <rect x="3" y="5" width="18" height="14" rx="3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4 7l8 6 8-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function SparkIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

/* --------------------------------- App / nav icons --------------------------------- */
// Shared by the sidebar nav (AppShell) and the per-page PageHeader tile, so the
// icon for a section is defined exactly once.

export function HomeIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path d="M4 11l8-6 8 6M6 10v9h12v-9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ArticleIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <rect x="5" y="3" width="14" height="18" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <path d="M9 8h6M9 12h6M9 16h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function LibraryIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <rect x="4" y="4" width="7" height="7" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <rect x="13" y="4" width="7" height="7" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <rect x="4" y="13" width="7" height="7" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <rect x="13" y="13" width="7" height="7" rx="2" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

export function CalendarIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <rect x="4" y="5" width="16" height="15" rx="3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4 9h16M8 3v4M16 3v4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function BrandIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.8" />
      <path d="M9 13c0-3 1.8-5 4-5M15 11c0 3-1.8 5-4 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function ChartIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path d="M5 19V10M12 19V5M19 19v-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 19h16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function SettingsIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 3v2.5M12 18.5V21M21 12h-2.5M5.5 12H3M18.4 5.6l-1.8 1.8M7.4 16.6l-1.8 1.8M18.4 18.4l-1.8-1.8M7.4 7.4 5.6 5.6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

/* ------------------------------- Empty-state art -------------------------------- */

export function EmptyDocs({ className }: IconProps) {
  return (
    <svg viewBox="0 0 120 100" fill="none" className={className} aria-hidden>
      <defs>
        <linearGradient id="og-empty-docs" x1="0" y1="0" x2="120" y2="100" gradientUnits="userSpaceOnUse">
          {GRAD_STOPS}
        </linearGradient>
      </defs>
      <rect x="26" y="16" width="58" height="72" rx="8" fill="#fff" stroke="#e5e7eb" strokeWidth="2" />
      <rect x="40" y="12" width="58" height="72" rx="8" fill="#fff" stroke="url(#og-empty-docs)" strokeWidth="2" />
      <rect x="50" y="28" width="38" height="5" rx="2.5" fill="#f1f5f9" />
      <rect x="50" y="40" width="30" height="5" rx="2.5" fill="#f1f5f9" />
      <rect x="50" y="52" width="34" height="5" rx="2.5" fill="#f1f5f9" />
      <circle cx="96" cy="72" r="12" fill="url(#og-empty-docs)" />
      <path d="M96 67v10M91 72h10" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export function EmptyCalendar({ className }: IconProps) {
  return (
    <svg viewBox="0 0 120 100" fill="none" className={className} aria-hidden>
      <defs>
        <linearGradient id="og-empty-cal" x1="0" y1="0" x2="120" y2="100" gradientUnits="userSpaceOnUse">
          {GRAD_STOPS}
        </linearGradient>
      </defs>
      <rect x="22" y="20" width="76" height="64" rx="10" fill="#fff" stroke="#e5e7eb" strokeWidth="2" />
      <rect x="22" y="20" width="76" height="18" rx="10" fill="url(#og-empty-cal)" />
      <rect x="34" y="14" width="5" height="12" rx="2.5" fill="#94a3b8" />
      <rect x="81" y="14" width="5" height="12" rx="2.5" fill="#94a3b8" />
      {[0, 1, 2, 3].map((c) =>
        [0, 1, 2].map((r) => (
          <rect key={`${c}-${r}`} x={34 + c * 14} y={48 + r * 11} width="8" height="8" rx="2" fill="#f1f5f9" />
        )),
      )}
    </svg>
  );
}

/* --------------------------------- Brand mark ----------------------------------- */

// Sprout "O" — a rising stem with two leaves inside a gradient tile.
/**
 * The `icon-forest` brand variant: forest container, white mark, one accent leaf.
 *
 * Corner radius is 22% of the side (8.8 on a 40 viewBox), per the brand sheet.
 * The drawing language here is still the shipped SILHOUETTE (filled leaves, no
 * centre veins, solid base dot). The sheet describes a monoline OUTLINE with
 * veins and an open base ring — closing that gap is a redraw, tracked as open
 * decision D1a. Only the colour and radius are brought to brand here.
 */
export function BrandMark({ className }: IconProps) {
  return (
    <svg viewBox="0 0 40 40" fill="none" className={className} aria-hidden>
      <rect width="40" height="40" rx="8.8" fill="#0B3B2E" />
      {/* stem */}
      <path
        d="M20 30 C 20 24, 20 20, 20 12"
        stroke="#fff"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
      {/* left leaf */}
      <path d="M20 23 C 14.5 23, 11 20, 11 15 C 16.5 15, 20 18, 20 23 Z" fill="#fff" />
      {/* right leaf (higher) — the accent leaf */}
      <path d="M20 19 C 25.5 19, 29 15.5, 29 10.5 C 23.5 10.5, 20 14, 20 19 Z" fill="#16A34A" />
      {/* base */}
      <circle cx="20" cy="30.5" r="1.7" fill="#fff" />
    </svg>
  );
}

/* ----------------------------- Decorative gradient mesh ------------------------- */

export function GradientMesh({ className }: IconProps) {
  return (
    <svg viewBox="0 0 400 300" className={className} aria-hidden preserveAspectRatio="xMidYMid slice">
      <defs>
        <radialGradient id="og-mesh-a" cx="20%" cy="20%" r="60%">
          <stop offset="0%" stopColor="#0B3B2E" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#0B3B2E" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="og-mesh-b" cx="80%" cy="30%" r="55%">
          <stop offset="0%" stopColor="#15803D" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#15803D" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="og-mesh-c" cx="50%" cy="90%" r="55%">
          <stop offset="0%" stopColor="#16A34A" stopOpacity="0.45" />
          <stop offset="100%" stopColor="#16A34A" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="400" height="300" fill="url(#og-mesh-a)" />
      <rect width="400" height="300" fill="url(#og-mesh-b)" />
      <rect width="400" height="300" fill="url(#og-mesh-c)" />
    </svg>
  );
}
