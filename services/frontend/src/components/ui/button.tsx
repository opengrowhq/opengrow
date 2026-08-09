"use client";

import { type ReactNode } from "react";
import { motion, type HTMLMotionProps } from "motion/react";
import { MotionLink, Spinner } from "@/components/motion";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "gradientOutline";
type Size = "sm" | "md" | "lg";

const base =
  "inline-flex select-none items-center justify-center gap-2 rounded-full font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-50";

const sizes: Record<Size, string> = {
  sm: "h-9 px-4 text-sm",
  md: "h-11 px-5 text-sm",
  lg: "h-14 px-8 text-base",
};

const variants: Record<Variant, string> = {
  // a11y: white label text needs 4.5:1. The gradient fill cannot provide it —
  // The brand interactive green #15803D is 5.02:1 against white; the retired
  // gradient could not clear 4.5:1 at any stop. Hover #12693A is 6.76:1. The
  // glow shadow is retained as decoration, retinted to the brand primary.
  primary: "bg-interactive text-white hover:bg-interactive-hover shadow-[0_10px_30px_rgba(11,59,46,0.20)]",
  // a11y: a button border IS the control boundary and needs 3:1. gray-300 is
  // 1.47:1 and gray-400 is 2.60:1 on white; gray-500 is 4.84:1.
  secondary: "border border-gray-500 bg-white text-gray-900 hover:border-gray-700 shadow-sm",
  ghost: "text-gray-700 hover:bg-gray-100",
  danger: "bg-red-600 text-white hover:bg-red-700",
  gradientOutline:
    "border-2 border-transparent bg-[linear-gradient(white,white),linear-gradient(90deg,#0B3B2E,#15803D,#16A34A)] [background-origin:border-box] [background-clip:padding-box,border-box] text-gradient",
};

const hover = { y: -2, scale: 1.02 };
const tap = { scale: 0.97 };
const springT = { type: "spring" as const, stiffness: 400, damping: 22 };

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  className,
  children,
  disabled,
  ...props
}: {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  className?: string;
  children: ReactNode;
} & Omit<HTMLMotionProps<"button">, "children" | "className">) {
  return (
    <motion.button
      whileHover={disabled || loading ? undefined : hover}
      whileTap={disabled || loading ? undefined : tap}
      transition={springT}
      disabled={disabled || loading}
      className={`${base} ${sizes[size]} ${variants[variant]} ${className ?? ""}`}
      {...props}
    >
      {loading && <Spinner size={16} className="border-white/40 border-t-white" />}
      {children}
    </motion.button>
  );
}

export function ButtonLink({
  href,
  variant = "primary",
  size = "md",
  className,
  children,
}: {
  href: string;
  variant?: Variant;
  size?: Size;
  className?: string;
  children: ReactNode;
}) {
  return (
    <MotionLink
      href={href}
      whileHover={hover}
      whileTap={tap}
      transition={springT}
      className={`${base} ${sizes[size]} ${variants[variant]} ${className ?? ""}`}
    >
      {children}
    </MotionLink>
  );
}
