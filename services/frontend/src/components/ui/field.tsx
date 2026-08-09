"use client";

import {
  type InputHTMLAttributes,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
  type ReactNode,
} from "react";

// Single source of truth for form-control styling.
//
// a11y: the control boundary and placeholder must clear WCAG minimums against
// white (#fff) and the app canvas (#F5F7FA). gray-300 (#D1D5DC) is 1.47:1 —
// below the 3:1 required of a non-text control boundary. gray-400 (#99A1AF)
// is 2.60:1 — below the 4.5:1 required of placeholder text. gray-500
// (#6A7282) is 4.84:1 on white / 4.51:1 on canvas and clears both.
//
// Vertical padding and the disabled treatment vary per surface, so they are
// passed in rather than baked in — appending a conflicting Tailwind utility
// (e.g. py-2.5 after py-3) would NOT reliably win, since precedence comes from
// the generated stylesheet order, not the className string.
const CONTROL_BASE =
  "w-full rounded-[var(--radius-md)] border border-gray-500 bg-white px-4 text-sm font-medium text-gray-900 outline-none transition placeholder:text-gray-500 focus:border-interactive focus:ring-4 focus:ring-focus-soft";

/** Compose the shared control style. `extra` supplies padding + disabled state. */
export function controlClass(extra = "py-3 disabled:opacity-50"): string {
  return `${CONTROL_BASE} ${extra}`;
}

const controlBase = controlClass();

export function Label({ children, htmlFor }: { children: ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block text-sm font-bold text-gray-800">
      {children}
    </label>
  );
}

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
}: {
  label?: ReactNode;
  htmlFor?: string;
  hint?: ReactNode;
  error?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div>
      {label && <Label htmlFor={htmlFor}>{label}</Label>}
      {children}
      {hint && !error && <p className="mt-1.5 text-xs font-medium text-gray-500">{hint}</p>}
      {error && <p className="mt-1.5 text-xs font-semibold text-red-600">{error}</p>}
    </div>
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${controlBase} ${className ?? ""}`} {...props} />;
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`${controlBase} resize-y ${className ?? ""}`} {...props} />;
}

export function Select({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={`${controlBase} cursor-pointer ${className ?? ""}`} {...props}>
      {children}
    </select>
  );
}
