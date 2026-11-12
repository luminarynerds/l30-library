/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { Bookmark, CheckCircle2, Clock, Package, XCircle, AlertTriangle, Calendar, Hash, Loader2 } from "lucide-react"
import type { Hold } from "../../../../api/api"

interface PatronHoldsTabProps {
  holds: Hold[]
  onCancelHold?: (holdId: number) => Promise<void>
  onCheckoutHold?: (holdId: number) => Promise<void>
}

type HoldDisplayStatus = "ready" | "pending" | "in-transit" | "fulfilled" | "cancelled" | "expired"

function mapHoldStatus(hold: Hold): HoldDisplayStatus {
  if (hold.is_ready || hold.status === "ready") return "ready"
  if (hold.status === "fulfilled") return "fulfilled"
  if (hold.status === "cancelled") return "cancelled"
  if (hold.status === "expired") return "expired"
  return "pending"
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

const holdStatusConfig: Record<HoldDisplayStatus, {
  label: string
  icon: typeof CheckCircle2
  badgeClass: string
}> = {
  ready: {
    label: "Ready for Pickup",
    icon: CheckCircle2,
    badgeClass: "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300",
  },
  pending: {
    label: "Pending",
    icon: Clock,
    badgeClass: "bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-300",
  },
  "in-transit": {
    label: "In Transit",
    icon: Package,
    badgeClass: "bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300",
  },
  fulfilled: {
    label: "Fulfilled",
    icon: CheckCircle2,
    badgeClass: "bg-lsc-cream text-lsc-dark/70 dark:bg-earth-800/50 dark:text-lsc-cream/70",
  },
  cancelled: {
    label: "Cancelled",
    icon: XCircle,
    badgeClass: "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400",
  },
  expired: {
    label: "Expired",
    icon: AlertTriangle,
    badgeClass: "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300",
  },
}

export function PatronHoldsTab({ holds, onCancelHold, onCheckoutHold }: PatronHoldsTabProps) {
  const [loadingActions, setLoadingActions] = useState<Record<string, boolean>>({})

  const hasActions = !!onCancelHold || !!onCheckoutHold

  async function handleAction(key: string, action: () => Promise<void>) {
    setLoadingActions((prev) => ({ ...prev, [key]: true }))
    try {
      await action()
    } finally {
      setLoadingActions((prev) => ({ ...prev, [key]: false }))
    }
  }

  if (!holds || holds.length === 0) {
    return (
      <div className="text-center py-16 text-lsc-dark/70 dark:text-lsc-cream/60">
        <Bookmark className="w-14 h-14 mx-auto mb-4 opacity-40 stroke-[1.5]" />
        <p className="text-lg font-medium mb-1">No active holds</p>
        <p className="text-sm">This patron has no items on hold.</p>
      </div>
    )
  }

  const readyCount = holds.filter((h) => mapHoldStatus(h) === "ready").length
  const pendingCount = holds.filter((h) => mapHoldStatus(h) === "pending").length

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <span className="font-medium text-lsc-dark dark:text-lsc-cream">
          {holds.length} hold{holds.length !== 1 ? "s" : ""}
        </span>
        {readyCount > 0 && (
          <span className="flex items-center gap-1 text-status-success-600 dark:text-status-success-400">
            <span className="w-2 h-2 rounded-full bg-status-success-500 inline-block" aria-hidden="true" />
            {readyCount} ready for pickup
          </span>
        )}
        {pendingCount > 0 && (
          <span className="flex items-center gap-1 text-status-info-600 dark:text-status-info-400">
            <span className="w-2 h-2 rounded-full bg-status-info-500 inline-block" aria-hidden="true" />
            {pendingCount} pending
          </span>
        )}
      </div>

      {/* Hold cards */}
      <div className="space-y-3">
        {holds.map((hold) => {
          const displayStatus = mapHoldStatus(hold)
          const config = holdStatusConfig[displayStatus]
          const StatusIcon = config.icon
          const queuePosition = hold.queue_position ?? hold.position
          const placedDate = hold.placed_at || hold.created_at

          return (
            <div
              key={hold.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 hover:border-lsc-primary/30 dark:hover:border-lsc-primary/30 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  {/* Title and author */}
                  <h4 className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={hold.item_title || "Unknown Title"}>
                    {hold.item_title || "Unknown Title"}
                  </h4>
                  {hold.item_author && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5 truncate" title={hold.item_author}>
                      {hold.item_author}
                    </p>
                  )}

                  {/* Detail row */}
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      Placed {formatDate(placedDate)}
                    </span>
                    {displayStatus === "pending" && queuePosition != null && queuePosition > 0 && (
                      <span className="flex items-center gap-1">
                        <Hash className="w-3.5 h-3.5" />
                        Position {queuePosition} in queue
                      </span>
                    )}
                    {hold.notified_at && (
                      <span className="text-status-success-600 dark:text-status-success-400">
                        Notified {formatDate(hold.notified_at)}
                      </span>
                    )}
                    {hold.expires_at && displayStatus === "ready" && (
                      <span className="text-status-warning-700 dark:text-status-warning-400">
                        Pickup by {formatDate(hold.expires_at)}
                      </span>
                    )}
                    {hold.cancelled_at && (
                      <span className="text-status-danger-600 dark:text-status-danger-400">
                        Cancelled {formatDate(hold.cancelled_at)}
                      </span>
                    )}
                  </div>

                  {/* Cancellation reason */}
                  {hold.cancellation_reason && (
                    <p className="mt-1.5 text-xs text-status-danger-700 dark:text-status-danger-300 italic">
                      Reason: {hold.cancellation_reason}
                    </p>
                  )}
                </div>

                {/* Status badge and actions */}
                <div className="flex-shrink-0 flex flex-col items-end gap-2">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.badgeClass}`}
                  >
                    <StatusIcon className="w-3.5 h-3.5" />
                    {config.label}
                  </span>

                  {hasActions && (displayStatus === "pending" || displayStatus === "ready") && (
                    <div className="flex items-center gap-1.5">
                      {onCheckoutHold && displayStatus === "ready" && (
                        <button
                          type="button"
                          disabled={!!loadingActions[`checkout-${hold.id}`]}
                          onClick={() => handleAction(`checkout-${hold.id}`, () => onCheckoutHold(hold.id))}
                          className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-lg text-status-success-800 bg-status-success-50 hover:bg-status-success-100 dark:text-status-success-200 dark:bg-status-success-900/20 dark:hover:bg-status-success-900/40 border border-status-success-200 dark:border-status-success-800 transition-colors disabled:opacity-50 min-h-[44px]"
                          title="Check out this hold to the patron"
                        >
                          {loadingActions[`checkout-${hold.id}`] ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <CheckCircle2 className="w-3.5 h-3.5" />
                          )}
                          Check Out
                        </button>
                      )}
                      {onCancelHold && (
                        <button
                          type="button"
                          disabled={!!loadingActions[`cancel-${hold.id}`]}
                          onClick={() => handleAction(`cancel-${hold.id}`, () => onCancelHold(hold.id))}
                          className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-lg text-status-danger-700 bg-status-danger-50 hover:bg-status-danger-100 dark:text-status-danger-300 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/40 border border-status-danger-200 dark:border-status-danger-800 transition-colors disabled:opacity-50 min-h-[44px]"
                          title="Cancel hold"
                        >
                          {loadingActions[`cancel-${hold.id}`] ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <XCircle className="w-3.5 h-3.5" />
                          )}
                          Cancel
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
