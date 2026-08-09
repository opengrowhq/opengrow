"use client";

import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { AnimatePresence, motion } from "motion/react";

type Tone = "success" | "error" | "info";
type Toast = { id: number; title: string; description?: string; tone: Tone };

type ToastInput = { title: string; description?: string; tone?: Tone };

const ToastContext = createContext<(t: ToastInput) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

const toneStyle: Record<Tone, { bar: string; icon: string }> = {
  success: { bar: "bg-emerald-500", icon: "✓" },
  error: { bar: "bg-red-500", icon: "!" },
  info: { bar: "bg-sky-500", icon: "i" },
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);

  const push = useCallback((t: ToastInput) => {
    const id = ++idRef.current;
    setToasts((prev) => [...prev, { id, tone: "info", ...t }]);
    setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 4200);
  }, []);

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-5 right-5 z-[60] flex w-[min(22rem,92vw)] flex-col gap-3">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, x: 40, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 40, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 300, damping: 26 }}
              className="pointer-events-auto flex items-start gap-3 overflow-hidden rounded-[var(--radius-md)] border border-gray-200 bg-white p-4 shadow-lift"
            >
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-black text-white ${toneStyle[t.tone].bar}`}
              >
                {toneStyle[t.tone].icon}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-bold text-gray-900">{t.title}</p>
                {t.description && (
                  <p className="mt-0.5 text-xs font-medium text-gray-500">{t.description}</p>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
