/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  AlertTriangle,
  RotateCcw,
  Trash2,
  Loader2,
} from "lucide-react"
import type { PullListItem } from "../types"

interface ExpiredHoldsViewProps {
  expiredHolds: PullListItem[]
  processingHoldId: number | null
  onRequeue: (holdId: number) => void
  onMarkNotPickedUp: (holdId: number) => void
}

export function ExpiredHoldsSectionView({
  expiredHolds,
  processingHoldId,
  onRequeue,
  onMarkNotPickedUp,
}: ExpiredHoldsViewProps) {
  if (expiredHolds.length === 0) return null

  return (
    <div className="mt-8 rounded-lg border border-status-danger-200 dark:border-status-danger-900/50 overflow-hidden bg-lsc-white dark:bg-earth-800">
      <div className="bg-status-danger-50 dark:bg-status-danger-900/20 px-6 py-4 border-b border-status-danger-200 dark:border-status-danger-900/50 flex items-center gap-3">
        <AlertTriangle className="h-5 w-5 text-status-danger-600" />
        <div>
          <h3 className="font-serif font-semibold text-status-danger-900 dark:text-status-danger-200">
            Expired Holds ({expiredHolds.length})
          </h3>
          <p className="text-sm text-status-danger-800 dark:text-status-danger-300 mt-0.5">
            These holds are past their pickup deadline and need to be cleared from the shelf
          </p>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
              <caption className="sr-only">Expired holds past their pickup deadline</caption>
          <thead>
            <tr className="border-b border-lsc-border dark:border-earth-700 bg-status-danger-50/50 dark:bg-status-danger-900/10">
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                Slot
              </th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                Patron
              </th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                Item Title
              </th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                Expired
              </th>
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {expiredHolds.map((item) => (
              <tr
                key={item.hold_id}
                className="border-b border-lsc-border dark:border-earth-700 bg-status-danger-50/30 dark:bg-status-danger-900/5 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/10"
              >
                <td className="px-4 py-4">
                  {item.shelf_slot ? (
                    <span className="inline-block bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-200 px-2 py-1 rounded font-mono font-bold text-sm">
                      {item.shelf_slot}
                    </span>
                  ) : (
                    <span className="text-earth-600 text-sm">-</span>
                  )}
                </td>
                <td className="px-4 py-4">
                  <div className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-status-danger-100 dark:bg-status-danger-900/30">
                      <span className="text-sm font-bold text-status-danger-600">
                        {item.patron_initials}
                      </span>
                    </div>
                    <div className="text-sm">
                      <div className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {item.patron_name}
                      </div>
                      <div className="text-lsc-dark/70 dark:text-lsc-cream/70">
                        {item.patron_library_card}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4">
                  <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    {item.item_title}
                  </div>
                  {item.item_author && (
                    <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {item.item_author}
                    </div>
                  )}
                </td>
                <td className="px-4 py-4">
                  <span className="text-sm font-bold text-status-danger-600">
                    {item.days_until_expiry !== null
                      ? `${Math.abs(item.days_until_expiry)} day${Math.abs(item.days_until_expiry) !== 1 ? "s" : ""} ago`
                      : "Unknown"}
                  </span>
                </td>
                <td className="px-4 py-4">
                  <div className="flex gap-1">
                    <button
                      onClick={() => onRequeue(item.hold_id)}
                      disabled={processingHoldId === item.hold_id}
                      className="flex items-center gap-1 px-2 py-1 text-xs bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-700 dark:text-status-warning-300 rounded hover:bg-status-warning-100 transition-colors disabled:opacity-50"
                      title="Re-queue to end of hold queue"
                    >
                      <RotateCcw className="h-3 w-3" />
                      Re-queue
                    </button>
                    <button
                      onClick={() => onMarkNotPickedUp(item.hold_id)}
                      disabled={processingHoldId === item.hold_id}
                      className="flex items-center gap-1 px-2 py-1 text-xs bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 rounded hover:bg-status-danger-100 transition-colors disabled:opacity-50"
                      title="Remove from shelf and advance queue"
                    >
                      {processingHoldId === item.hold_id ? (
                        <Loader2 className="h-3 w-3 motion-safe:animate-spin" />
                      ) : (
                        <Trash2 className="h-3 w-3" />
                      )}
                      Clear
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
