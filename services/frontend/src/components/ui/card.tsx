"use client";

import { type ReactNode } from "react";
import { motion } from "motion/react";

/** Surface card. Set `hover` for a lift micro-interaction, `glass` for blur. */
export function Card({
  children,
  className,
  hover = false,
  glass = false,
  padded = true,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  glass?: boolean;
  padded?: boolean;
}) {
  const surface = glass
    ? "border border-gray-200/70 bg-white/70 backdrop-blur-xl"
    : "border border-gray-200 bg-white";
  return (
    <motion.div
      whileHover={hover ? { y: -6 } : undefined}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
      className={`rounded-[var(--radius-lg)] shadow-card ${surface} ${
        hover ? "transition-shadow hover:shadow-lift" : ""
      } ${padded ? "p-6" : ""} ${className ?? ""}`}
    >
      {children}
    </motion.div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
  className,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex items-start justify-between gap-4 ${className ?? ""}`}>
      <div>
        <h3 className="text-lg font-black tracking-tight text-gray-950">{title}</h3>
        {subtitle && <p className="mt-1 text-sm font-medium text-gray-500">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
