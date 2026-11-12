/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { User, X, Mail, Phone, CreditCard, Loader2, CheckCircle2, Barcode } from "lucide-react"
import { useTranslation, formatCurrency } from "@/i18n"
import { isValidBarcodeFormat } from "../types"
import type { Patron } from "../types"
import { InlineErrorDisplay } from "./InlineErrorDisplay"
import type { CheckoutError } from "./InlineErrorDisplay"

interface QuickCheckoutSectionProps {
  selectedPatron: Patron
  itemBarcode: string
  setItemBarcode: (barcode: string) => void
  isCheckingOut: boolean
  checkoutSuccess: boolean
  handleCheckout: (e: React.FormEvent) => void
  clearPatron: () => void
  checkoutInputRef: React.RefObject<HTMLInputElement>
  checkoutError?: CheckoutError | null
  onDismissError?: () => void
  onShowErrorDetails?: () => void
}

export function QuickCheckoutSection({
  selectedPatron,
  itemBarcode,
  setItemBarcode,
  isCheckingOut,
  checkoutSuccess,
  handleCheckout,
  clearPatron,
  checkoutInputRef,
  checkoutError,
  onDismissError,
  onShowErrorDetails,
}: QuickCheckoutSectionProps): React.ReactElement {
  const { t, language } = useTranslation()

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 md:p-6 shadow-sm">
      <div className="flex items-start justify-between mb-3 md:mb-4">
        <h2 className="font-serif text-base md:text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{t('staffCirculation.selectedPatron')} <kbd className="ml-2 px-1.5 py-0.5 text-xs font-mono bg-lsc-cream dark:bg-lsc-brown rounded hidden md:inline-block">Esc</kbd></h2>
        <button aria-label={t('staffCirculation.deselectPatron')} onClick={clearPatron} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-lg"><X aria-hidden="true" className="w-5 h-5" /></button>
      </div>
      <div className="flex items-center gap-3 md:gap-4 mb-3 md:mb-4">
        <div className="w-12 h-12 md:w-16 md:h-16 bg-lsc-cream dark:bg-lsc-brown/30 rounded-full flex items-center justify-center flex-shrink-0"><User aria-hidden="true" className="w-6 h-6 md:w-8 md:h-8 text-lsc-rose dark:text-lsc-rose-light" /></div>
        <div className="min-w-0">
          <p className="text-lg md:text-xl font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={`${selectedPatron.first_name} ${selectedPatron.last_name}`}>{selectedPatron.first_name} {selectedPatron.last_name}</p>
          <div className="flex flex-wrap items-center gap-1.5 mt-1">
            {!selectedPatron.is_active && <span className="inline-block px-2 py-0.5 text-xs font-medium bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400 rounded">{t('staffCirculation.patronBlocked')}</span>}
            {(selectedPatron.fines_balance ?? 0) > 0 ? (
              <span className="inline-block px-2 py-0.5 text-xs font-medium bg-status-danger-100 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 rounded">{t('staffCirculation.patronOwed', { amount: formatCurrency(selectedPatron.fines_balance!, language, 'USD') })}</span>
            ) : selectedPatron.fines_balance !== undefined ? (
              <span className="inline-block px-2 py-0.5 text-xs font-medium bg-status-success-100 dark:bg-status-success-900/20 text-status-success-700 dark:text-status-success-300 rounded">{t('staffCirculation.patronNoFines')}</span>
            ) : null}
          </div>
        </div>
      </div>
      <div className="space-y-1.5 md:space-y-2 text-xs md:text-sm">
        <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={selectedPatron.email ?? selectedPatron.email_masked ?? undefined}><Mail aria-hidden="true" className="w-4 h-4 flex-shrink-0" /><span className="truncate">{selectedPatron.email ?? selectedPatron.email_masked ?? ""}</span></div>
        {selectedPatron.phone && <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70"><Phone aria-hidden="true" className="w-4 h-4 flex-shrink-0" />{selectedPatron.phone}</div>}
        {selectedPatron.library_card && <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70"><CreditCard aria-hidden="true" className="w-4 h-4 flex-shrink-0" /><span className="font-mono">{selectedPatron.library_card}</span></div>}
      </div>
      <div className="mt-4 pt-4 border-t border-lsc-border dark:border-earth-700">
        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">{t('staffCirculation.quickCheckout')} <kbd className="ml-2 px-1.5 py-0.5 text-xs font-mono bg-lsc-cream dark:bg-lsc-brown rounded hidden md:inline-block">C</kbd></h3>
        <form onSubmit={handleCheckout} className="flex gap-2">
          <div className="relative flex-1">
            <input ref={checkoutInputRef} type="text" value={itemBarcode} onChange={(e) => setItemBarcode(e.target.value.toUpperCase())} aria-label={t('aria.staffCirculation.itemBarcode')} placeholder={t('staffCirculation.scanOrEnterItemBarcode')} className={`w-full pl-3 pr-10 md:pl-4 md:pr-12 py-2 rounded-xl border bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent font-mono text-sm md:text-base transition-colors ${checkoutSuccess ? "border-status-success-500 bg-status-success-50 dark:bg-status-success-900/20" : isValidBarcodeFormat(itemBarcode) ? "border-lsc-rose/50" : "border-lsc-border dark:border-earth-700"}`} disabled={!selectedPatron.is_active} />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
              {isCheckingOut ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
              ) : checkoutSuccess ? (
                <CheckCircle2 className="w-4 h-4 text-status-success-500" aria-hidden="true" />
              ) : isValidBarcodeFormat(itemBarcode) ? (
                <Barcode className="w-4 h-4 text-lsc-rose/70" aria-hidden="true" />
              ) : itemBarcode.length > 0 ? (
                <Barcode className="w-4 h-4 text-lsc-dark/30 dark:text-lsc-cream/60" aria-hidden="true" />
              ) : null}
            </div>
          </div>
          <button type="submit" disabled={isCheckingOut || !selectedPatron.is_active || !isValidBarcodeFormat(itemBarcode)} aria-label={t('staffCirculation.checkOutItem')} className="px-3 md:px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl font-medium text-sm md:text-base transition-colors">{isCheckingOut ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : t('staffCirculation.tabCheckOut')}</button>
        </form>
        <InlineErrorDisplay
          error={checkoutError ?? null}
          onDismiss={onDismissError ?? (() => {})}
          onShowDetails={onShowErrorDetails}
        />
        {!selectedPatron.is_active && <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-2">{t('staffCirculation.thisPatronIsBlockedAnd')}</p>}
        {/* Screen reader announcement for checkout status */}
        <div aria-live="polite" aria-atomic="true" className="sr-only">
          {isCheckingOut ? t('staffCirculation.checkingOutItem') : checkoutSuccess ? t('staffCirculation.itemCheckedOutSuccess') : ''}
        </div>
      </div>
    </div>
  )
}
