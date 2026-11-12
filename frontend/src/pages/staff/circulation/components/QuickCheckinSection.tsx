/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, CheckCircle2, Barcode } from "lucide-react"
import { useTranslation } from "@/i18n"
import { isValidBarcodeFormat } from "../types"

interface QuickCheckinSectionProps {
  checkinBarcode: string
  setCheckinBarcode: (barcode: string) => void
  isCheckingIn: boolean
  checkinSuccess: boolean
  handleCheckin: (e: React.FormEvent) => void
  checkinInputRef: React.RefObject<HTMLInputElement>
}

export function QuickCheckinSection({
  checkinBarcode,
  setCheckinBarcode,
  isCheckingIn,
  checkinSuccess,
  handleCheckin,
  checkinInputRef,
}: QuickCheckinSectionProps): React.ReactElement {
  const { t } = useTranslation()

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 md:p-6 shadow-sm">
      <h2 className="font-serif text-base md:text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 md:mb-4">{t('staffCirculation.quickCheckin')} <kbd className="ml-2 px-1.5 py-0.5 text-xs font-mono bg-lsc-cream dark:bg-lsc-brown rounded hidden md:inline-block">I</kbd></h2>
      <form onSubmit={handleCheckin} className="flex gap-2">
        <div className="relative flex-1">
          <input ref={checkinInputRef} type="text" value={checkinBarcode} onChange={(e) => setCheckinBarcode(e.target.value.toUpperCase())} aria-label={t('aria.staffCirculation.itemBarcode')} placeholder={t('staffCirculation.scanOrEnterItemBarcode2')} className={`w-full pl-3 pr-10 md:pl-4 md:pr-12 py-2 rounded-xl border bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent font-mono text-sm md:text-base transition-colors ${checkinSuccess ? "border-status-success-500 bg-status-success-50 dark:bg-status-success-900/20" : isValidBarcodeFormat(checkinBarcode) ? "border-lsc-rose/50" : "border-lsc-border dark:border-earth-700"}`} />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
            {isCheckingIn ? (
              <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
            ) : checkinSuccess ? (
              <CheckCircle2 className="w-4 h-4 text-status-success-500" aria-hidden="true" />
            ) : isValidBarcodeFormat(checkinBarcode) ? (
              <Barcode className="w-4 h-4 text-lsc-rose/70" aria-hidden="true" />
            ) : checkinBarcode.length > 0 ? (
              <Barcode className="w-4 h-4 text-lsc-dark/30 dark:text-lsc-cream/60" aria-hidden="true" />
            ) : null}
          </div>
        </div>
        <button type="submit" disabled={isCheckingIn || !isValidBarcodeFormat(checkinBarcode)} aria-label={t('staffCirculation.checkInItem')} className="px-3 md:px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl font-medium text-sm md:text-base transition-colors">{isCheckingIn ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : t('staffCirculation.tabCheckIn')}</button>
      </form>
      {/* Screen reader announcement for checkin status */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {isCheckingIn ? t('staffCirculation.checkingInItem') : checkinSuccess ? t('staffCirculation.itemCheckedInSuccess') : ''}
      </div>
    </div>
  )
}
