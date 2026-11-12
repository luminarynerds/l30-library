/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { BookOpen, Calendar, Clock, AlertTriangle, CheckCircle2, AlertCircle, RotateCcw, LogIn, Loader2 } from "lucide-react"
import type { PatronCheckout } from "../../../../api/api"

interface PatronCheckoutsTabProps {
  checkouts: PatronCheckout[]
  onRenew?: (checkoutId: number) => void
  onCheckIn?: (checkoutId: number) => void
}

type DueStatus = "overdue" | "due-soon" | "normal"

function getDueStatus(dueDateStr: string): DueStatus {
  const now = new Date()
  const due = new Date(dueDateStr)
  const diffMs = due.getTime() - now.getTime()
  const diffDays = diffMs / (1000 * 60 * 60 * 24)

  if (diffDays < 0) return "overdue"
  if (diffDays <= 3) return "due-soon"
  return "normal"
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

function getDaysOverdue(dueDateStr: string): number {
  const now = new Date()
  const due = new Date(dueDateStr)
  return Math.ceil((now.getTime() - due.getTime()) / (1000 * 60 * 60 * 24))
}

function getDaysUntilDue(dueDateStr: string): number {
  const now = new Date()
  const due = new Date(dueDateStr)
  return Math.floor((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
}

const statusConfig: Record<DueStatus, {
  label: string
  icon: typeof AlertTriangle
  dotClass: string
  badgeClass: string
}> = {
  overdue: {
    label: "Overdue",
    icon: AlertCircle,
    dotClass: "bg-status-danger-500",
    badgeClass: "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300",
  },
  "due-soon": {
    label: "Due Soon",
    icon: AlertTriangle,
    dotClass: "bg-status-warning-500",
    badgeClass: "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300",
  },
  normal: {
    label: "On Time",
    icon: CheckCircle2,
    dotClass: "bg-status-success-500",
    badgeClass: "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300",
  },
}

export function PatronCheckoutsTab({ checkouts, onRenew, onCheckIn }: PatronCheckoutsTabProps) {
  const [loadingItems, setLoadingItems] = useState<Record<number, "renew" | "checkin">>({})
  const hasActions = !!(onRenew || onCheckIn)

  const handleAction = async (checkoutId: number, action: "renew" | "checkin") => {
    const handler = action === "renew" ? onRenew : onCheckIn
    if (!handler) return
    setLoadingItems((prev) => ({ ...prev, [checkoutId]: action }))
    try {
      await handler(checkoutId)
    } finally {
      setLoadingItems((prev) => {
        const next = { ...prev }
        delete next[checkoutId]
        return next
      })
    }
  }

  if (!checkouts || checkouts.length === 0) {
    return (
      <div className="text-center py-16 text-lsc-dark/70 dark:text-lsc-cream/60">
        <BookOpen className="w-14 h-14 mx-auto mb-4 opacity-40 stroke-[1.5]" />
        <p className="text-lg font-medium mb-1">No active checkouts</p>
        <p className="text-sm">This patron has no items currently checked out.</p>
      </div>
    )
  }

  const overdueCount = checkouts.filter((c) => getDueStatus(c.due_date) === "overdue").length
  const dueSoonCount = checkouts.filter((c) => getDueStatus(c.due_date) === "due-soon").length

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <span className="font-medium text-lsc-dark dark:text-lsc-cream">
          {checkouts.length} item{checkouts.length !== 1 ? "s" : ""} checked out
        </span>
        {overdueCount > 0 && (
          <span className="flex items-center gap-1 text-status-danger-600 dark:text-status-danger-400">
            <span className="w-2 h-2 rounded-full bg-status-danger-500 inline-block" aria-hidden="true" />
            {overdueCount} overdue
          </span>
        )}
        {dueSoonCount > 0 && (
          <span className="flex items-center gap-1 text-status-warning-700 dark:text-status-warning-400">
            <span className="w-2 h-2 rounded-full bg-status-warning-500 inline-block" aria-hidden="true" />
            {dueSoonCount} due soon
          </span>
        )}
      </div>

      {/* Checkout cards */}
      <div className="space-y-3">
        {checkouts.map((checkout) => {
          const dueStatus = getDueStatus(checkout.due_date)
          const config = statusConfig[dueStatus]
          const StatusIcon = config.icon

          return (
            <div
              key={checkout.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 hover:border-lsc-primary/30 dark:hover:border-lsc-primary/30 transition-colors"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  {/* Title and author */}
                  <h4 className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={checkout.item_title || "Unknown Title"}>
                    {checkout.item_title || "Unknown Title"}
                  </h4>
                  {checkout.item_author && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5 truncate" title={checkout.item_author}>
                      {checkout.item_author}
                    </p>
                  )}

                  {/* Date details */}
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                    {checkout.checked_out_at && (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        Checked out {formatDate(checkout.checked_out_at)}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      Due {formatDate(checkout.due_date)}
                    </span>
                    {checkout.renewal_count != null && checkout.renewal_count > 0 && (
                      <span className="text-lsc-primary dark:text-lsc-primary/80">
                        Renewed {checkout.renewal_count}x
                      </span>
                    )}
                  </div>
                </div>

                {/* Status badge */}
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.badgeClass}`}
                  >
                    <StatusIcon className="w-3.5 h-3.5" />
                    {config.label}
                  </span>
                  {dueStatus === "overdue" && (
                    <span className="text-xs text-status-danger-600 dark:text-status-danger-400 font-medium">
                      {getDaysOverdue(checkout.due_date)} day{getDaysOverdue(checkout.due_date) !== 1 ? "s" : ""} overdue
                    </span>
                  )}
                  {dueStatus === "due-soon" && (
                    <span className="text-xs text-status-warning-700 dark:text-status-warning-400 font-medium">
                      {getDaysUntilDue(checkout.due_date)} day{getDaysUntilDue(checkout.due_date) !== 1 ? "s" : ""} left
                    </span>
                  )}
                </div>
              </div>

              {/* Action buttons */}
              {hasActions && (
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-lsc-border/50 dark:border-earth-700/50">
                  {onRenew && dueStatus !== "overdue" && (
                    <button
                      onClick={() => handleAction(checkout.id, "renew")}
                      disabled={!!loadingItems[checkout.id]}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loadingItems[checkout.id] === "renew" ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <RotateCcw className="w-3.5 h-3.5" />
                      )}
                      Renew
                    </button>
                  )}
                  {onCheckIn && (
                    <button
                      onClick={() => handleAction(checkout.id, "checkin")}
                      disabled={!!loadingItems[checkout.id]}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-lsc-rose/10 text-lsc-rose hover:bg-lsc-rose/20 dark:bg-lsc-rose/20 dark:hover:bg-lsc-rose/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loadingItems[checkout.id] === "checkin" ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <LogIn className="w-3.5 h-3.5" />
                      )}
                      Check In
                    </button>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
