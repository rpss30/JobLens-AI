"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

const DISMISS_AFTER_MS = 5000;

export type ToastTone = "success" | "error";

interface Toast {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastContextValue {
  showToast: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextIdRef = useRef(1);
  const timersRef = useRef<number[]>([]);

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, tone: ToastTone = "success") => {
      const id = nextIdRef.current++;

      setToasts((current) => [...current, { id, message, tone }]);

      const timer = window.setTimeout(() => dismissToast(id), DISMISS_AFTER_MS);
      timersRef.current.push(timer);
    },
    [dismissToast],
  );

  useEffect(
    () => () => {
      timersRef.current.forEach((timer) => window.clearTimeout(timer));
    },
    [],
  );

  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}

      {/* Polite live region so screen readers hear confirmations too. */}
      <div
        role="status"
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex w-full max-w-md items-start justify-between gap-3 rounded-xl border px-4 py-3 shadow-lg ${
              toast.tone === "error"
                ? "border-status-offline/40 bg-surface text-text"
                : "border-border bg-surface text-text"
            }`}
          >
            <span className="flex items-start gap-2 text-sm">
              <span
                aria-hidden="true"
                className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                  toast.tone === "error"
                    ? "bg-status-offline"
                    : "bg-status-online"
                }`}
              />
              {toast.message}
            </span>
            <button
              type="button"
              onClick={() => dismissToast(toast.id)}
              className="-mr-1 rounded p-1 text-text-subtle hover:text-text"
            >
              <span className="sr-only">Dismiss notification</span>
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
                <path
                  d="M1.5 1.5l7 7m0-7l-7 7"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);

  if (!context) {
    throw new Error("useToast must be used inside a ToastProvider.");
  }

  return context;
}
