/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Toast Notification System
 *
 * Provides accessible toast notifications that respect accessibility settings:
 * - whisperMode: suppresses non-critical toasts
 * - reduceMotion: disables slide animations
 * - autoDismissSeconds: configurable auto-dismiss timing
 * - aria-live regions for screen reader announcements
 *
 * Usage:
 *   const { toast, dismiss } = useToast()
 *   toast({ message: "Item checked out", type: "success" })
 *   toast({ message: "Undo?", type: "info", action: { label: "Undo", onClick: handleUndo } })
 */

import { createContext, useContext, useCallback, useState, useRef, useEffect, type ReactNode } from "react";
import { X, CheckCircle2, AlertTriangle, Info, AlertCircle } from "lucide-react";
import { useUnifiedAccessibility } from "@/features/accessibility/hooks/useUnifiedAccessibility";

// --- Types ---

export type ToastType = "success" | "error" | "warning" | "info";
export type ToastPriority = "normal" | "critical";

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface ToastOptions {
  message: string;
  type?: ToastType;
  priority?: ToastPriority;
  duration?: number; // ms, overrides default
  action?: ToastAction;
  dismissible?: boolean;
}

interface ToastItem extends Required<Pick<ToastOptions, "message" | "type" | "priority" | "dismissible">> {
  id: string;
  action?: ToastAction;
  duration: number;
  createdAt: number;
}

interface ToastContextValue {
  toast: (options: ToastOptions) => string;
  dismiss: (id: string) => void;
  dismissAll: () => void;
}

// --- Context ---

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

// --- Provider ---

const DEFAULT_DURATION = 5000;
const MAX_VISIBLE = 3;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());
  const { settings } = useUnifiedAccessibility();

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const dismissAll = useCallback(() => {
    timersRef.current.forEach((timer) => clearTimeout(timer));
    timersRef.current.clear();
    setToasts([]);
  }, []);

  const toast = useCallback(
    (options: ToastOptions): string => {
      // Respect whisperMode: suppress non-critical toasts
      if (settings.whisperMode && (options.priority ?? "normal") !== "critical") {
        return "";
      }

      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const duration =
        options.duration ??
        (settings.autoDismissSeconds ? settings.autoDismissSeconds * 1000 : DEFAULT_DURATION);

      const item: ToastItem = {
        id,
        message: options.message,
        type: options.type ?? "info",
        priority: options.priority ?? "normal",
        dismissible: options.dismissible ?? true,
        action: options.action,
        duration,
        createdAt: Date.now(),
      };

      setToasts((prev) => {
        const next = [...prev, item];
        // Evict oldest if over max
        if (next.length > MAX_VISIBLE) {
          const evicted = next.shift()!;
          const timer = timersRef.current.get(evicted.id);
          if (timer) {
            clearTimeout(timer);
            timersRef.current.delete(evicted.id);
          }
        }
        return next;
      });

      // Auto-dismiss (unless action present -- those stay until interacted with)
      if (!options.action) {
        const timer = setTimeout(() => dismiss(id), duration);
        timersRef.current.set(id, timer);
      }

      return id;
    },
    [settings.whisperMode, settings.autoDismissSeconds, dismiss]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      timersRef.current.forEach((timer) => clearTimeout(timer));
    };
  }, []);

  return (
    <ToastContext.Provider value={{ toast, dismiss, dismissAll }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

// --- Renderer ---

const ICONS: Record<ToastType, typeof CheckCircle2> = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const TYPE_STYLES: Record<ToastType, string> = {
  success: "border-status-success-300 dark:border-status-success-700 bg-status-success-50 dark:bg-status-success-900/50 text-status-success-800 dark:text-status-success-200",
  error: "border-status-danger-300 dark:border-status-danger-700 bg-status-danger-50 dark:bg-status-danger-900/50 text-status-danger-800 dark:text-status-danger-200",
  warning: "border-status-warning-300 dark:border-status-warning-700 bg-status-warning-50 dark:bg-status-warning-900/50 text-status-warning-800 dark:text-status-warning-200",
  info: "border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream",
};

function ToastContainer({ toasts, onDismiss }: { toasts: ToastItem[]; onDismiss: (id: string) => void }) {
  const { settings } = useUnifiedAccessibility();
  const reduceMotion = settings.reduceMotion;

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-20 sm:bottom-4 left-4 right-4 sm:left-auto sm:right-4 z-[9980] flex flex-col gap-2 sm:w-80 max-w-[calc(100vw-2rem)] print:hidden"
      aria-live="polite"
      aria-atomic="false"
      role="region"
      aria-label="Notifications"
    >
      {toasts.map((item) => {
        const Icon = ICONS[item.type];
        return (
          <div
            key={item.id}
            className={`
              flex items-start gap-3 p-3 rounded-lg border shadow-lg
              ${TYPE_STYLES[item.type]}
              ${reduceMotion ? "" : "motion-safe:animate-slide-in-right"}
            `}
            role="status"
          >
            <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">{item.message}</p>
              {item.action && (
                <button
                  onClick={() => {
                    item.action!.onClick();
                    onDismiss(item.id);
                  }}
                  className="mt-1 text-sm font-semibold underline hover:no-underline focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1"
                >
                  {item.action.label}
                </button>
              )}
            </div>
            {item.dismissible && (
              <button
                onClick={() => onDismiss(item.id)}
                className="flex-shrink-0 p-1 rounded hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                aria-label="Dismiss notification"
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default ToastProvider;
