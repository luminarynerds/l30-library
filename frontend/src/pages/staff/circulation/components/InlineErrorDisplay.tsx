/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle, XCircle, AlertCircle, Info, X } from "lucide-react"

export type CheckoutErrorType = "not_found" | "blocked" | "hold_conflict" | "patron_issue" | "unknown"

export interface CheckoutError {
  type: CheckoutErrorType
  message: string
  suggestion?: string
  hasProblemDetails?: boolean
}

interface InlineErrorDisplayProps {
  error: CheckoutError | null
  onDismiss: () => void
  onShowDetails?: () => void
}

const errorConfig: Record<CheckoutErrorType, {
  icon: typeof AlertTriangle
  bg: string
  border: string
  text: string
  iconColor: string
}> = {
  not_found: {
    icon: AlertTriangle,
    bg: "bg-status-warning-50 dark:bg-status-warning-900/20",
    border: "border-status-warning-300 dark:border-status-warning-700",
    text: "text-status-warning-800 dark:text-status-warning-200",
    iconColor: "text-status-warning-600 dark:text-status-warning-400",
  },
  blocked: {
    icon: XCircle,
    bg: "bg-status-danger-50 dark:bg-status-danger-900/20",
    border: "border-status-danger-300 dark:border-status-danger-700",
    text: "text-status-danger-800 dark:text-status-danger-200",
    iconColor: "text-status-danger-600 dark:text-status-danger-400",
  },
  hold_conflict: {
    icon: Info,
    bg: "bg-status-info-50 dark:bg-status-info-900/20",
    border: "border-status-info-300 dark:border-status-info-700",
    text: "text-status-info-800 dark:text-status-info-200",
    iconColor: "text-status-info-600 dark:text-status-info-400",
  },
  patron_issue: {
    icon: AlertCircle,
    bg: "bg-status-warning-50 dark:bg-status-warning-900/20",
    border: "border-status-warning-300 dark:border-status-warning-700",
    text: "text-status-warning-800 dark:text-status-warning-200",
    iconColor: "text-status-warning-600 dark:text-status-warning-400",
  },
  unknown: {
    icon: AlertCircle,
    bg: "bg-status-danger-50 dark:bg-status-danger-900/20",
    border: "border-status-danger-300 dark:border-status-danger-700",
    text: "text-status-danger-800 dark:text-status-danger-200",
    iconColor: "text-status-danger-600 dark:text-status-danger-400",
  },
}

export function InlineErrorDisplay({ error, onDismiss, onShowDetails }: InlineErrorDisplayProps): React.ReactElement | null {
  if (!error) return null

  const config = errorConfig[error.type]
  const Icon = config.icon

  return (
    <div
      className={`mt-2 flex items-start gap-2 rounded-lg border px-3 py-2 ${config.bg} ${config.border} ${config.text}`}
      role="alert"
    >
      <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${config.iconColor}`} aria-hidden="true" />
      <div className="flex-1 min-w-0 text-sm">
        <p>{error.message}</p>
        {error.suggestion && (
          <p className="mt-0.5 opacity-80 text-xs">{error.suggestion}</p>
        )}
        {error.hasProblemDetails && onShowDetails && (
          <button
            type="button"
            onClick={onShowDetails}
            className="mt-1 text-xs font-medium underline underline-offset-2 hover:opacity-80"
          >
            Show Details
          </button>
        )}
      </div>
      <button
        type="button"
        onClick={onDismiss}
        className={`flex-shrink-0 p-0.5 rounded hover:opacity-70 ${config.iconColor}`}
        aria-label="Dismiss error"
      >
        <X className="w-3.5 h-3.5" aria-hidden="true" />
      </button>
    </div>
  )
}
