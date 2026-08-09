"use client";

// Canonical shared motion primitives for the whole app (core + hosted overlay).
// Every primitive degrades gracefully under prefers-reduced-motion (renders the
// final, visible state with no animation) and animates transform/opacity only so
// it stays on the compositor at 60fps.

import { type CSSProperties, type ReactNode, useEffect, useRef, useState } from "react";
import NextLink from "next/link";
import {
  animate,
  motion,
  useInView,
  useReducedMotion,
  type Transition,
  type Variants,
} from "motion/react";

// Premium ease-out (expo-like) used across the design system.
export const EASE = [0.22, 1, 0.36, 1] as const;
export const spring: Transition = { type: "spring", stiffness: 300, damping: 30, mass: 0.7 };
export const softSpring: Transition = { type: "spring", stiffness: 170, damping: 26 };

/** Animated Next.js Link — for CTAs that press / lift. */
export const MotionLink = motion.create(NextLink);

/** Fade + rise as the element scrolls into view. */
export function Reveal({
  children,
  delay = 0,
  y = 26,
  className,
  style,
}: {
  children: ReactNode;
  delay?: number;
  y?: number;
  className?: string;
  style?: CSSProperties;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      style={style}
      initial={reduce ? false : { opacity: 0, y }}
      whileInView={reduce ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  );
}

const containerVariants: Variants = {
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.05 } },
};

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
};

/** Container that reveals its <StaggerItem> children in sequence on scroll. */
export function Stagger({
  children,
  className,
  amount = 0.2,
}: {
  children: ReactNode;
  className?: string;
  amount?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : "hidden"}
      whileInView={reduce ? undefined : "show"}
      viewport={{ once: true, amount }}
      variants={containerVariants}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className,
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div className={className} style={style} variants={reduce ? undefined : staggerItem}>
      {children}
    </motion.div>
  );
}

/** Count-up number that starts when scrolled into view. */
export function Counter({
  to,
  duration = 1.8,
  className,
  format,
}: {
  to: number;
  duration?: number;
  className?: string;
  format?: (value: number) => string;
}) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!inView || reduce) return;
    const controls = animate(0, to, {
      duration,
      ease: EASE,
      onUpdate: (v) => setValue(v),
    });
    return () => controls.stop();
  }, [inView, to, duration, reduce]);

  const fmt = format ?? ((v: number) => Math.round(v).toLocaleString());
  const shown = reduce ? to : value;
  return (
    <span ref={ref} className={className}>
      {fmt(shown)}
    </span>
  );
}

/** Seamless infinite marquee. `children` is rendered twice for the loop. */
export function Marquee({
  children,
  speed = 32,
  className,
}: {
  children: ReactNode;
  speed?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();
  if (reduce) {
    return <div className={`flex flex-wrap justify-center gap-4 ${className ?? ""}`}>{children}</div>;
  }
  return (
    <div className={`group overflow-hidden ${className ?? ""}`}>
      <motion.div
        className="flex w-max gap-4"
        animate={{ x: ["0%", "-50%"] }}
        transition={{ duration: speed, ease: "linear", repeat: Infinity }}
      >
        <div className="flex shrink-0 gap-4">{children}</div>
        <div className="flex shrink-0 gap-4" aria-hidden>
          {children}
        </div>
      </motion.div>
    </div>
  );
}

/** Slow-drifting blurred gradient orbs for premium section backgrounds. */
export function Aurora({ className }: { className?: string }) {
  const reduce = useReducedMotion();
  const float: Transition | undefined = reduce
    ? undefined
    : { duration: 14, ease: "easeInOut", repeat: Infinity, repeatType: "mirror" };
  return (
    <div className={`pointer-events-none absolute inset-0 -z-10 overflow-hidden ${className ?? ""}`}>
      <motion.div
        className="absolute -left-24 top-0 h-[26rem] w-[26rem] rounded-full bg-og-green-600/20 blur-[110px]"
        animate={reduce ? undefined : { x: [0, 40, 0], y: [0, 30, 0] }}
        transition={float}
      />
      <motion.div
        className="absolute right-0 top-24 h-[30rem] w-[30rem] rounded-full bg-og-green-400/20 blur-[120px]"
        animate={reduce ? undefined : { x: [0, -50, 0], y: [0, 40, 0] }}
        transition={float}
      />
      <motion.div
        className="absolute bottom-0 left-1/3 h-[24rem] w-[24rem] rounded-full bg-og-green-200/25 blur-[110px]"
        animate={reduce ? undefined : { x: [0, 30, 0], y: [0, -30, 0] }}
        transition={float}
      />
    </div>
  );
}

/** Route/page transition wrapper — used from app/template.tsx. */
export function PageTransition({ children }: { children: ReactNode }) {
  const reduce = useReducedMotion();
  if (reduce) return <>{children}</>;
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

/** Shimmering skeleton block for loading states. */
export function Skeleton({
  className,
  rounded = "rounded-xl",
  style,
}: {
  className?: string;
  rounded?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      className={`relative overflow-hidden bg-gray-200/60 ${rounded} ${className ?? ""}`}
      style={style}
      aria-hidden
    >
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/70 to-transparent"
        initial={{ x: "-100%" }}
        animate={{ x: "100%" }}
        transition={{ duration: 1.4, ease: "easeInOut", repeat: Infinity }}
      />
    </div>
  );
}

/** Circular gradient spinner. */
export function Spinner({ size = 20, className }: { size?: number; className?: string }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 border-gray-300 border-t-gray-900 ${className ?? ""}`}
      style={{ width: size, height: size }}
      role="status"
      aria-label="Loading"
    />
  );
}

/** Fade/slide/scale presence wrapper for lists and reveals. */
export { motion, AnimatePresence } from "motion/react";
