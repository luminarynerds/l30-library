/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import {
  Book, Clock, Calendar, AlertCircle, RefreshCw, Loader2,
} from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { Checkout } from '../../services/api'
import type { EbookBorrow } from '@/api/indie-catalog-api'
import type { MetisLibCheckout } from '@/api/domains/catalog/metislib-api'

type UnifiedCheckoutItem =
  | { type: 'library'; data: Checkout }
  | { type: 'indie'; data: EbookBorrow }
  | { type: 'metislib'; data: MetisLibCheckout }

interface CheckoutsTabProps {
  unifiedCheckouts: UnifiedCheckoutItem[]
  checkoutsLoading: boolean
  indieBorrowsLoading: boolean
  renewingId: number | null
  returningBorrowId: number | null
  onRefresh: () => void
  onRenew: (id: number) => void
  onReturnBorrow: (id: number) => void
  formatDate: (dateStr: string) => string
  isOverdue: (dueDate: string) => boolean
}

export function CheckoutsTab({
  unifiedCheckouts,
  checkoutsLoading,
  indieBorrowsLoading,
  renewingId,
  returningBorrowId,
  onRefresh,
  onRenew,
  onReturnBorrow,
  formatDate,
  isOverdue,
}: CheckoutsTabProps): React.ReactElement {
  const { t } = useTranslation()
  const [confirmReturnId, setConfirmReturnId] = useState<number | null>(null)

  function handleReturnClick(id: number) {
    setConfirmReturnId(id)
  }

  function handleConfirmReturn(id: number) {
    setConfirmReturnId(null)
    onReturnBorrow(id)
  }

  function handleKeepBorrow() {
    setConfirmReturnId(null)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('account.myCheckouts')}</h2>
        <button
          onClick={onRefresh}
          disabled={checkoutsLoading || indieBorrowsLoading}
          aria-label={t('account.refreshCheckouts')}
          className="flex items-center gap-2 px-3 py-2 text-lsc-dark/70 hover:text-lsc-dark transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
        >
          <RefreshCw className={`w-5 h-5 ${(checkoutsLoading || indieBorrowsLoading) ? 'motion-safe:animate-spin' : ''}`} />
          {t('account.refresh')}
        </button>
      </div>

      {(checkoutsLoading && indieBorrowsLoading) ? (
        <div className="flex justify-center py-12" role="status">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
        </div>
      ) : unifiedCheckouts.length === 0 ? (
        <div className="text-center py-12">
          <Book className="w-12 h-12 text-sage/30 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('account.noActiveCheckouts')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {unifiedCheckouts.map(item => {
            const isLibrary = item.type === 'library'
            const isMetislib = item.type === 'metislib'
            const isIndie = item.type === 'indie'
            const key = isLibrary ? `lib-${item.data.id}` : isMetislib ? `ml-${item.data.access_id}` : `indie-${item.data.id}`
            const title = isLibrary ? item.data.item_title : isMetislib ? item.data.title : item.data.ebook_title
            const author = isLibrary ? item.data.item_author : isMetislib ? item.data.author_name : item.data.author_pen_name
            const checkedOutDate = isLibrary ? item.data.checked_out_at : isMetislib ? null : item.data.borrowed_at
            const dueDate = isLibrary ? item.data.due_date : isMetislib ? item.data.expires_at : item.data.due_at
            const overdue = dueDate ? isOverdue(dueDate) : false
            const renewalsRemaining = isLibrary ? item.data.renewals_remaining : undefined
            const canRenew = renewalsRemaining === undefined || renewalsRemaining > 0

            return (
              <div
                key={key}
                className={`p-4 rounded-xl border-2 ${
                  overdue ? 'border-status-danger-300 dark:border-status-danger-700 bg-status-danger-50 dark:bg-status-danger-900/20' : 'border-lsc-border bg-lsc-cream dark:bg-earth-800'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-full ${
                        isLibrary
                          ? 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/50 dark:text-status-info-300'
                          : 'bg-category-100 text-category-800 dark:bg-category-900/50 dark:text-category-300'
                      }`}>
                        {isLibrary ? t('account.book') : t('account.ebook')}
                      </span>
                    </div>
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream text-lg">{title}</h3>
                    {author && (
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-1">{t('account.byAuthor')} {author}</p>
                    )}
                    <div className="flex flex-wrap items-center gap-4 mt-3 text-sm">
                      <div className="flex items-center gap-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                        <Calendar className="w-4 h-4" aria-hidden="true" />
                        <span>{checkedOutDate ? (isLibrary ? t('account.checkedOut', { date: formatDate(checkedOutDate) }) : t('account.borrowed', { date: formatDate(checkedOutDate) })) : t('account.ebook')}</span>
                      </div>
                      <div className={`flex items-center gap-1 ${
                        overdue ? 'text-status-danger-600 font-semibold' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                      }`}>
                        <Clock className="w-4 h-4" aria-hidden="true" />
                        <span>{dueDate ? t('account.dueDate', { date: formatDate(dueDate) }) : t('account.noExpiry')}</span>
                        {overdue && <AlertCircle className="w-4 h-4 ml-1" aria-hidden="true" />}
                      </div>
                      {isLibrary && renewalsRemaining !== undefined && (
                        <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${
                          renewalsRemaining === 0
                            ? 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300'
                            : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
                        }`}>
                          <RefreshCw className="w-3 h-3" aria-hidden="true" />
                          {renewalsRemaining === 0
                            ? t('account.noRenewalsLeft')
                            : t('account.renewalsLeft', { count: renewalsRemaining })}
                        </span>
                      )}
                    </div>
                  </div>
                  {isLibrary ? (
                    <button
                      onClick={() => onRenew(item.data.id)}
                      disabled={renewingId === item.data.id || !canRenew}
                      title={!canRenew ? t('account.noRenewalsLeft') : undefined}
                      className="ml-4 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                    >
                      {renewingId === item.data.id ? (
                        <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4" />
                      )}
                      {t('account.renew')}
                    </button>
                  ) : isMetislib ? (
                    item.data.download_url && (
                      <a
                        href={item.data.download_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-4 px-4 py-2 bg-category-600 text-white rounded-xl hover:bg-category-700 transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                      >
                        <Book className="w-4 h-4" />
                        {t('account.read')}
                      </a>
                    )
                  ) : isIndie ? (
                    <div className="ml-4 flex-shrink-0">
                      {confirmReturnId === item.data.id ? (
                        <div
                          className="flex flex-col gap-2 p-3 rounded-xl border-2 border-status-warning-300 dark:border-status-warning-700 bg-status-warning-50 dark:bg-status-warning-900/20"
                          role="group"
                          aria-label={t('account.returnEarlyConfirmTitle')}
                        >
                          <p className="text-sm font-medium text-status-warning-700 dark:text-status-warning-300">
                            {t('account.returnEarlyConfirmPrompt')}
                          </p>
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleConfirmReturn(item.data.id)}
                              disabled={returningBorrowId === item.data.id}
                              className="px-3 py-1.5 text-sm bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 flex items-center gap-1"
                            >
                              {returningBorrowId === item.data.id ? (
                                <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" />
                              ) : null}
                              {t('account.yesReturnEarly')}
                            </button>
                            <button
                              onClick={handleKeepBorrow}
                              className="px-3 py-1.5 text-sm bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-100 dark:hover:bg-earth-600 transition-colors border border-lsc-border dark:border-earth-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                            >
                              {t('account.keepBorrow')}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleReturnClick(item.data.id)}
                          disabled={returningBorrowId === item.data.id}
                          className="px-4 py-2 bg-category-600 text-white rounded-xl hover:bg-category-700 transition-colors disabled:opacity-50 flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                        >
                          {returningBorrowId === item.data.id ? (
                            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                          ) : (
                            <Book className="w-4 h-4" />
                          )}
                          {t('account.returnEarly')}
                        </button>
                      )}
                    </div>
                  ) : null}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
