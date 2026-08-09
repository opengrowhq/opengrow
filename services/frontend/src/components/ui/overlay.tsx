"use client";

import { type ReactNode, useEffect } from "react";
import { AnimatePresence, motion } from "motion/react";
import { EASE } from "@/components/motion";

/* ---------------------------------- Modal ----------------------------------- */

export function Modal({
  open,
  onClose,
  children,
  className,
  labelledBy,
}: {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  className?: string;
  labelledBy?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/40 p-5 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby={labelledBy}
            initial={{ opacity: 0, scale: 0.95, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ type: "spring", stiffness: 300, damping: 26 }}
            onClick={(e) => e.stopPropagation()}
            className={`w-full max-w-lg rounded-[var(--radius-lg)] border border-gray-200 bg-white p-6 shadow-lift ${className ?? ""}`}
          >
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* ---------------------------------- Drawer ---------------------------------- */

export function Drawer({
  open,
  onClose,
  children,
  side = "right",
  className,
}: {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  side?: "right" | "left" | "bottom";
  className?: string;
}) {
  const off =
    side === "right"
      ? { x: "100%" }
      : side === "left"
        ? { x: "-100%" }
        : { y: "100%" };
  const pos =
    side === "bottom"
      ? "inset-x-0 bottom-0 rounded-t-[var(--radius-xl)]"
      : side === "right"
        ? "inset-y-0 right-0 w-[min(22rem,90vw)]"
        : "inset-y-0 left-0 w-[min(22rem,90vw)]";
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-gray-950/40 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.aside
            initial={off}
            animate={{ x: 0, y: 0 }}
            exit={off}
            transition={{ type: "spring", stiffness: 300, damping: 32 }}
            onClick={(e) => e.stopPropagation()}
            className={`absolute border-gray-200 bg-white shadow-lift ${pos} ${className ?? ""}`}
          >
            {children}
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* --------------------------------- Tooltip ---------------------------------- */

export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className="group/tip relative inline-flex">
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 translate-y-1 whitespace-nowrap rounded-lg bg-gray-900 px-2.5 py-1.5 text-xs font-semibold text-white opacity-0 transition-all duration-150 group-hover/tip:translate-y-0 group-hover/tip:opacity-100"
      >
        {label}
      </span>
    </span>
  );
}

export { EASE };
