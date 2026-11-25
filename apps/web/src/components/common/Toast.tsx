import { useEffect, useState } from "react";

export type ToastVariant = "success" | "info" | "error";

interface ToastAction {
  label: string;
  onClick: () => void;
}

interface ToastItem {
  id: number;
  message: string;
  detail?: string;
  variant: ToastVariant;
  action?: ToastAction;
  durationMs: number;
}

type ToastListener = (toast: ToastItem) => void;

const listeners = new Set<ToastListener>();
let nextToastId = 1;

/** Dispatches a transient top-center toast notification anywhere in the app. */
export function showToast(
  message: string,
  options?: {
    detail?: string;
    variant?: ToastVariant;
    action?: ToastAction;
    durationMs?: number;
  }
) {
  const item: ToastItem = {
    id: nextToastId++,
    message,
    detail: options?.detail,
    variant: options?.variant ?? "success",
    action: options?.action,
    durationMs: options?.durationMs ?? (options?.action ? 5000 : 2200),
  };
  listeners.forEach((fn) => fn(item));
}

const VARIANT_STYLES: Record<ToastVariant, string> = {
  success: "border-emerald-500/40 text-[var(--text-primary)]",
  info: "border-[var(--border-strong)] text-[var(--text-primary)]",
  error: "border-rose-500/40 text-rose-500",
};

/** Global top-center toast container mounted once at the application root. */
export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    const timers: number[] = [];
    const onToast: ToastListener = (item) => {
      setToasts((prev) => [...prev.slice(-2), item]);
      const timer = window.setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== item.id));
      }, item.durationMs);
      timers.push(timer);
    };
    listeners.add(onToast);
    return () => {
      listeners.delete(onToast);
      timers.forEach((id) => window.clearTimeout(id));
    };
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed top-4 left-1/2 z-50 flex -translate-x-1/2 flex-col items-center gap-2 px-4"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={`pointer-events-auto flex max-w-md items-center gap-2 rounded-md border bg-[var(--bg-surface)] px-3.5 py-2 text-xs shadow-md ${VARIANT_STYLES[toast.variant]}`}
        >
          {toast.variant === "success" && (
            <span className="font-mono text-emerald-500" aria-hidden="true">
              ✓
            </span>
          )}
          {toast.variant === "error" && (
            <span className="font-mono text-rose-500" aria-hidden="true">
              ✕
            </span>
          )}
          {toast.variant === "info" && (
            <span className="font-mono text-[var(--text-muted)]" aria-hidden="true">
              •
            </span>
          )}
          <span className="font-medium">{toast.message}</span>
          {toast.detail && (
            <code className="max-w-[200px] truncate rounded bg-[var(--bg-subtle)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--text-secondary)]">
              {toast.detail}
            </code>
          )}
          {toast.action && (
            <button
              type="button"
              onClick={() => {
                setToasts((prev) => prev.filter((t) => t.id !== toast.id));
                toast.action?.onClick();
              }}
              className="ml-1 rounded border border-[var(--border-strong)] bg-[var(--bg-subtle)] px-2 py-0.5 font-semibold text-[var(--text-primary)] transition hover:bg-[var(--bg-canvas)]"
            >
              {toast.action.label}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
