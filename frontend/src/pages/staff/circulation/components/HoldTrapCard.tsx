/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Bookmark, Printer, X } from "lucide-react"
import type { NextHoldInfo } from "@/api/staff-api/circulation"
import { useTranslation } from "@/i18n"

interface HoldTrapCardProps {
  nextHold: NextHoldInfo
  onDismiss: () => void
  onPrint?: () => void
}

function formatExpiryDate(iso: string | null): string | null {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
}

export function HoldTrapCard({ nextHold, onDismiss, onPrint }: HoldTrapCardProps): React.ReactElement {
  const { t } = useTranslation()
  const initials = `${nextHold.patron_first_name} ${nextHold.patron_last_initial}`.trim()
  const slot = nextHold.shelf_slot
  const expiry = formatExpiryDate(nextHold.expires_at)

  const handlePrint = () => {
    if (onPrint) onPrint()
    // Caller decides whether to print; default fallback for callers that omit
    // onPrint just opens the browser print dialog and the .print-only slip
    // beneath this card renders the layout.
    if (!onPrint) window.print()
  }

  return (
    <>
      <div
        role="status"
        aria-live="polite"
        className="sticky top-2 z-20 bg-amber-50 dark:bg-amber-900/30 border-2 border-amber-400 dark:border-amber-600 rounded-xl p-4 md:p-5 shadow-md print:hidden"
        data-testid="hold-trap-card"
      >
        <div className="flex items-start gap-3">
          <Bookmark className="w-6 h-6 text-amber-600 dark:text-amber-300 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div className="flex-1 min-w-0">
            <p className="font-serif text-base md:text-lg font-semibold text-amber-900 dark:text-amber-100">
              {t('staffCirculation.holdTrap.placeOnShelfFor', { initials })}
              {slot ? t('staffCirculation.holdTrap.slotSuffix', { slot }) : ""}
            </p>
            {!slot && (
              <p className="text-xs text-amber-800 dark:text-amber-200 mt-1">
                {t('staffCirculation.holdTrap.slotNotAssigned')}
              </p>
            )}
            {nextHold.item_title && (
              <p className="text-sm text-amber-800 dark:text-amber-200 mt-1 truncate">
                {nextHold.item_title}
              </p>
            )}
            {expiry && (
              <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
                {t('staffCirculation.holdTrap.pickupDeadline', { date: expiry })}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrint}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-700 hover:bg-amber-800 text-white rounded-lg text-sm font-medium transition-colors"
              data-testid="hold-trap-print"
            >
              <Printer className="w-4 h-4" aria-hidden="true" />
              {t('staffCirculation.holdTrap.printSlip')}
            </button>
            <button
              type="button"
              onClick={onDismiss}
              aria-label={t('staffCirculation.holdTrap.dismissAria')}
              className="p-1.5 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-800 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      {/* Print-only slip (hidden on screen via global print.css .print-only) */}
      <div className="print-only" aria-hidden="true">
        <div style={{ padding: "16px", fontFamily: "monospace" }}>
          <h2 style={{ fontSize: "18px", marginBottom: "8px" }}>{t('staffCirculation.holdTrap.holdShelfHeader')}</h2>
          <p style={{ fontSize: "32px", fontWeight: "bold", margin: "12px 0" }}>{initials}</p>
          {slot && <p style={{ fontSize: "20px", margin: "8px 0" }}>{t('staffCirculation.holdTrap.slotLabel', { slot })}</p>}
          {nextHold.item_title && (
            <p style={{ fontSize: "16px", margin: "8px 0" }}>{nextHold.item_title}</p>
          )}
          {expiry && (
            <p style={{ fontSize: "14px", margin: "8px 0" }}>{t('staffCirculation.holdTrap.pickupByLabel', { date: expiry })}</p>
          )}
          <p style={{ fontSize: "12px", marginTop: "12px", color: "#555" }}>
            {t('staffCirculation.holdTrap.holdNumber', { id: nextHold.hold_id })}
          </p>
        </div>
      </div>
    </>
  )
}
