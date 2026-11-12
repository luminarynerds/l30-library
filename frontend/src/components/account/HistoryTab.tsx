/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { History, RefreshCw, Loader2, Settings } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { Checkout } from '../../services/api'

interface HistoryTabProps {
  history: Checkout[]
  historyLoading: boolean
  onRefresh: () => void
  formatDate: (dateStr: string) => string
  onSetTab?: (tab: string) => void
}

export function HistoryTab({
  history,
  historyLoading,
  onRefresh,
  formatDate,
  onSetTab,
}: HistoryTabProps): React.ReactElement {
  const { t } = useTranslation()

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('account.checkoutHistory')}</h2>
        <button
          onClick={onRefresh}
          disabled={historyLoading}
          aria-label={t('account.refreshHistory')}
          className="flex items-center gap-2 px-3 py-2 text-lsc-dark/70 hover:text-lsc-dark transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
        >
          <RefreshCw className={`w-5 h-5 ${historyLoading ? 'motion-safe:animate-spin' : ''}`} />
          {t('account.refresh')}
        </button>
      </div>

      {historyLoading ? (
        <div className="flex justify-center py-12" role="status">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
        </div>
      ) : history.length === 0 ? (
        <div className="text-center py-12">
          <History className="w-12 h-12 text-sage/30 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('account.noHistory')}</p>
          <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50 mt-3 max-w-sm mx-auto">
            {t('account.historyTrackingOffExplanation')}
          </p>
          {onSetTab && (
            <button
              type="button"
              onClick={() => onSetTab('settings')}
              className="inline-flex items-center gap-1.5 mt-3 text-sm text-lsc-rose hover:text-lsc-rose/80 font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded px-2 py-1"
            >
              <Settings className="w-3.5 h-3.5" aria-hidden="true" />
              {t('account.manageInSettings')}
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {history.map(item => (
            <div key={item.id} className="p-4 rounded-xl bg-cream dark:bg-earth-800">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{item.item_title}</h3>
              {item.item_author && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream mt-1">{t('account.byAuthor')} {item.item_author}</p>
              )}
              <div className="flex items-center gap-4 mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <span>{t('account.checkedOut', { date: formatDate(item.checked_out_at) })}</span>
                {item.returned_at && <span>{t('account.returned', { date: formatDate(item.returned_at) })}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
