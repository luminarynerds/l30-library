/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  CheckCircle2,
  Navigation,
  RotateCcw,
  Trash2,
} from "lucide-react"
import { useTranslation } from "@/i18n"
import type { ExpiringHoldsResponse } from "../types"

interface ExpiringHoldsViewProps {
  expiringHolds: ExpiringHoldsResponse
  processingHoldId: number | null
  onRequeue: (holdId: number) => void
  onMarkNotPickedUp: (holdId: number) => void
}

export function ExpiringHoldsView({
  expiringHolds,
  processingHoldId,
  onRequeue,
  onMarkNotPickedUp,
}: ExpiringHoldsViewProps) {
  const { t } = useTranslation()

  return (
    <div className="rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden bg-lsc-white dark:bg-earth-800">
      <div className="bg-status-danger-50 dark:bg-status-danger-900/20 px-6 py-4 border-b border-lsc-border dark:border-earth-700">
        <h3 className="font-serif font-semibold text-status-danger-900 dark:text-status-danger-200">
          Holds Expiring in 48 Hours ({expiringHolds.total_expiring})
        </h3>
        <p className="text-sm text-status-danger-800 dark:text-status-danger-300 mt-1">
          Sorted by expiration time - most urgent first
        </p>
      </div>
      {expiringHolds.holds.length === 0 ? (
        <div className="p-12 text-center">
          <CheckCircle2 className="h-12 w-12 text-status-success-400 mx-auto mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">
            No holds expiring in the next 48 hours
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
              <caption className="sr-only">Holds expiring within the next 48 hours</caption>
            <thead>
              <tr className="border-b border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900">
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                  Slot
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                  Patron
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                  Item
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                  Expires In
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                  Status
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {expiringHolds.holds.map((hold) => (
                <tr
                  key={hold.hold_id}
                  className="border-b border-lsc-border dark:border-earth-700 hover:bg-earth-50 dark:hover:bg-earth-800"
                >
                  <td className="px-6 py-4">
                    {hold.shelf_slot ? (
                      <span className="inline-block bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-200 px-2 py-1 rounded font-mono font-bold text-sm">
                        {hold.shelf_slot}
                      </span>
                    ) : (
                      <span className="text-earth-600 text-sm">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-earth-100 dark:bg-earth-800/30">
                        <span className="text-sm font-bold text-lsc-rose dark:text-lsc-rose-light">
                          {hold.patron_initials}
                        </span>
                      </div>
                      <div className="text-sm">
                        <div className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {hold.patron_name}
                        </div>
                        <div className="text-lsc-dark/70 dark:text-lsc-cream/70">
                          {hold.patron_library_card}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {hold.item_title}
                    </div>
                    {hold.item_author && (
                      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {hold.item_author}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`font-bold text-sm ${
                        hold.hours_until_expiry !== null && hold.hours_until_expiry <= 6
                          ? "text-status-danger-600"
                          : hold.hours_until_expiry !== null &&
                              hold.hours_until_expiry <= 24
                            ? "text-status-warning-700"
                            : "text-status-warning-700"
                      }`}
                    >
                      {hold.hours_until_expiry !== null
                        ? hold.hours_until_expiry <= 1
                          ? "< 1 hr"
                          : `${Math.round(hold.hours_until_expiry)} hrs`
                        : "Unknown"}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {hold.patron_on_way && (
                      <span className="inline-flex items-center gap-1 text-lsc-rose dark:text-lsc-rose-light text-sm font-medium">
                        <Navigation className="h-3 w-3" /> On Way
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-1">
                      <button
                        onClick={() => onRequeue(hold.hold_id)}
                        disabled={processingHoldId === hold.hold_id}
                        className="flex items-center gap-1 px-2 py-1 text-xs bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-700 dark:text-status-warning-300 rounded hover:bg-status-warning-100 transition-colors disabled:opacity-50"
                        title={t('staffHoldShelf.reQueueToEndOf')}
                      >
                        <RotateCcw className="h-3 w-3" />
                        Re-queue
                      </button>
                      <button
                        onClick={() => onMarkNotPickedUp(hold.hold_id)}
                        disabled={processingHoldId === hold.hold_id}
                        className="flex items-center gap-1 px-2 py-1 text-xs bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 rounded hover:bg-status-danger-100 transition-colors disabled:opacity-50"
                        title={t('staffHoldShelf.expireAndAdvanceQueue')}
                      >
                        <Trash2 className="h-3 w-3" />
                        Remove
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
