/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { Book, Calendar, AlertTriangle, Loader2, Info, DollarSign, Clock } from "lucide-react"
import { useTranslation, formatCurrency } from "@/i18n"
import { formatDate, isOverdue } from "../types"
import type { Patron, PatronCheckout } from "../types"

const DAILY_FINE_RATE = 0.25
const MAX_FINE_PER_ITEM = 10.0

function getDaysOverdue(dueDate: string): number {
  const due = new Date(dueDate)
  const now = new Date()
  const diffMs = now.getTime() - due.getTime()
  return Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)))
}

function getDaysUntilDue(dueDate: string): number {
  const due = new Date(dueDate)
  const now = new Date()
  const diffMs = due.getTime() - now.getTime()
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24))
}

function calculateFine(dueDate: string): number {
  const days = getDaysOverdue(dueDate)
  if (days <= 0) return 0
  return Math.min(days * DAILY_FINE_RATE, MAX_FINE_PER_ITEM)
}

function isDueToday(dueDate: string): boolean {
  const due = new Date(dueDate)
  const now = new Date()
  return (
    due.getFullYear() === now.getFullYear() &&
    due.getMonth() === now.getMonth() &&
    due.getDate() === now.getDate()
  )
}

function isDueSoon(dueDate: string): boolean {
  const days = getDaysUntilDue(dueDate)
  return days > 0 && days <= 3
}

interface CurrentCheckoutsListProps {
  selectedPatron: Patron
  patronCheckouts: PatronCheckout[]
  loadingCheckouts: boolean
  isRenewingAll: boolean
  onRenewAllClick: () => void
  renewKeyLabel?: string
}

export function CurrentCheckoutsList({
  selectedPatron,
  patronCheckouts,
  loadingCheckouts,
  isRenewingAll,
  onRenewAllClick,
  renewKeyLabel = 'R',
}: CurrentCheckoutsListProps): React.ReactElement {
  const { t, language } = useTranslation()
  const [showFineInfo, setShowFineInfo] = useState(false)
  const fmt = (amount: number): string => formatCurrency(amount, language, 'USD')

  const overdueCheckouts = patronCheckouts.filter((c) => isOverdue(c.due_date))
  const totalProjectedFines = overdueCheckouts.reduce(
    (sum, c) => sum + calculateFine(c.due_date),
    0
  )

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 md:p-6 shadow-sm">
      <div className="flex items-center justify-between mb-3 md:mb-4">
        <h2 className="font-serif text-base md:text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{t('staffCirculation.checkouts.currentCheckoutsTitle', { count: patronCheckouts.length })}</h2>
        {patronCheckouts.length > 0 && selectedPatron.is_active && (
          <button
            onClick={onRenewAllClick}
            disabled={isRenewingAll}
            className="flex items-center gap-2 px-2 md:px-3 py-1.5 text-xs md:text-sm font-medium bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-lg transition-colors"
            aria-label={t('staffCirculation.renewAllEligibleItemsR')}
            title={`Keyboard shortcut: ${renewKeyLabel}`}
          >
            {isRenewingAll ? <Loader2 className="w-3 h-3 motion-safe:animate-spin" aria-hidden="true" /> : <span>{t('staffCirculation.checkouts.renewAll')}</span>}
            <kbd className="hidden md:inline-block px-1 py-0.5 text-xs font-mono bg-lsc-rose/30 rounded">{renewKeyLabel}</kbd>
          </button>
        )}
      </div>
      {/* Screen reader announcement for checkouts loading state */}
      <div role="status" aria-live="polite" className="sr-only">
        {loadingCheckouts
          ? t('staffCirculation.checkouts.loadingCheckouts')
          : (patronCheckouts.length === 1
              ? t('staffCirculation.checkouts.itemsCheckedOutOne', { count: patronCheckouts.length })
              : t('staffCirculation.checkouts.itemsCheckedOutOther', { count: patronCheckouts.length }))}
      </div>
      {/* Fine projection summary */}
      {!loadingCheckouts && overdueCheckouts.length > 0 && (
        <div className="flex items-center gap-2 mb-3 p-2 md:p-3 rounded-lg bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800/40">
          <DollarSign className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0" aria-hidden="true" />
          <p className="text-xs md:text-sm text-status-danger-700 dark:text-status-danger-300 flex-1">
            <span className="font-medium">
              {overdueCheckouts.length === 1
                ? t('staffCirculation.checkouts.overdueItemsOne', { count: overdueCheckouts.length })
                : t('staffCirculation.checkouts.overdueItemsOther', { count: overdueCheckouts.length })}
            </span>
            {' '}&mdash; {t('staffCirculation.checkouts.projectedFinesLabel')} <span className="font-semibold">{fmt(totalProjectedFines)}</span>
          </p>
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowFineInfo((v) => !v)}
              className="p-0.5 rounded-full text-status-danger-500 dark:text-status-danger-400 hover:bg-status-danger-100 dark:hover:bg-status-danger-800/30 transition-colors"
              aria-label={t('staffCirculation.checkouts.fineRateInfoLabel')}
              aria-expanded={showFineInfo}
            >
              <Info className="w-3.5 h-3.5" />
            </button>
            {showFineInfo && (
              <div className="absolute right-0 top-6 z-10 w-56 p-2.5 rounded-lg bg-lsc-white dark:bg-earth-700 shadow-lg border border-lsc-border dark:border-earth-600 text-xs text-lsc-dark/80 dark:text-lsc-cream/80">
                <p className="font-medium mb-1">{t('staffCirculation.checkouts.finePolicyHeading')}</p>
                <p>{t('staffCirculation.checkouts.finePolicyDailyRate', { rate: fmt(DAILY_FINE_RATE) })}</p>
                <p>{t('staffCirculation.checkouts.finePolicyMaximum', { max: fmt(MAX_FINE_PER_ITEM) })}</p>
                <p className="mt-1 text-lsc-dark/60 dark:text-lsc-cream/60">{t('staffCirculation.checkouts.finePolicyFootnote')}</p>
              </div>
            )}
          </div>
        </div>
      )}
      {loadingCheckouts ? (
        <div className="flex items-center justify-center py-6 md:py-8"><Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" /></div>
      ) : patronCheckouts.length === 0 ? (
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-6 md:py-8 text-sm md:text-base">{t('staffCirculation.noItemsCheckedOut')}</p>
      ) : (
        <div className="space-y-2 md:space-y-3">
          {patronCheckouts.map((checkout) => {
            const overdue = isOverdue(checkout.due_date)
            const dueToday = isDueToday(checkout.due_date)
            const dueSoon = isDueSoon(checkout.due_date)
            const fine = calculateFine(checkout.due_date)
            const daysOver = getDaysOverdue(checkout.due_date)

            return (
              <div key={checkout.id} className={`flex items-start gap-2 md:gap-3 p-2 md:p-3 rounded-xl ${overdue ? "bg-status-danger-50 dark:bg-status-danger-900/10 border border-status-danger-200/60 dark:border-status-danger-800/30" : dueToday ? "bg-status-warning-50 dark:bg-status-warning-900/10 border border-status-warning-200/60 dark:border-status-warning-800/30" : dueSoon ? "bg-status-warning-50/50 dark:bg-status-warning-900/5 border border-status-warning-100 dark:border-status-warning-900/20" : "bg-lsc-cream dark:bg-lsc-brown/50"}`}>
                <Book className={`w-4 h-4 md:w-5 md:h-5 mt-0.5 flex-shrink-0 ${overdue ? "text-status-danger-500 dark:text-status-danger-400" : dueToday ? "text-status-warning-600 dark:text-status-warning-400" : dueSoon ? "text-status-warning-500 dark:text-status-warning-400" : "text-lsc-dark dark:text-lsc-cream/80"}`} />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream text-sm md:text-base truncate" title={checkout.item_title || t('staffCirculation.checkouts.unknownItem')}>{checkout.item_title || t('staffCirculation.checkouts.unknownItem')}</p>
                  {checkout.item_author && <p className="text-xs md:text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={t('staffCirculation.checkouts.byAuthor', { author: checkout.item_author })}>{t('staffCirculation.checkouts.byAuthor', { author: checkout.item_author })}</p>}
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1">
                    {overdue ? (
                      <>
                        <span className="flex items-center gap-1 text-xs font-medium text-status-danger-600 dark:text-status-danger-400">
                          <AlertTriangle aria-hidden="true" className="w-3 h-3" />
                          {t('staffCirculation.checkouts.overdueWasDue', { date: formatDate(checkout.due_date) })}
                        </span>
                        <span className="text-xs font-semibold text-status-danger-600 dark:text-status-danger-400">
                          {daysOver === 1
                            ? t('staffCirculation.checkouts.fineAccruedOne', { amount: fmt(fine), count: daysOver })
                            : t('staffCirculation.checkouts.fineAccruedOther', { amount: fmt(fine), count: daysOver })}
                        </span>
                      </>
                    ) : dueToday ? (
                      <>
                        <span className="flex items-center gap-1 text-xs font-bold text-status-warning-700 dark:text-status-warning-300">
                          <Clock aria-hidden="true" className="w-3 h-3" />
                          {t('staffCirculation.checkouts.dueToday')}
                        </span>
                        <span className="text-xs text-status-warning-600 dark:text-status-warning-400">
                          {t('staffCirculation.checkouts.rateAfterToday', { rate: fmt(DAILY_FINE_RATE) })}
                        </span>
                      </>
                    ) : dueSoon ? (
                      <>
                        <span className="flex items-center gap-1 text-xs text-status-warning-600 dark:text-status-warning-400">
                          <Calendar aria-hidden="true" className="w-3 h-3" />
                          {t('staffCirculation.checkouts.dueDate', { date: formatDate(checkout.due_date) })}
                        </span>
                        <span className="text-xs text-status-warning-500 dark:text-status-warning-400/80">
                          {t('staffCirculation.checkouts.rateAfterDueDate', { rate: fmt(DAILY_FINE_RATE) })}
                        </span>
                      </>
                    ) : (
                      <span className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        <Calendar aria-hidden="true" className="w-3 h-3" />
                        {t('staffCirculation.checkouts.dueDate', { date: formatDate(checkout.due_date) })}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
