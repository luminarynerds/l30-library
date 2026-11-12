/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Clock, Calendar, AlertCircle, RefreshCw, Loader2, MapPin } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { Hold } from '../../services/api'

interface HoldsTabProps {
  holds: Hold[]
  holdsLoading: boolean
  cancellingId: number | null
  onRefresh: () => void
  onCancel: (holdId: number) => void
  formatDate: (dateStr: string) => string
}

export function HoldsTab({
  holds,
  holdsLoading,
  cancellingId,
  onRefresh,
  onCancel,
  formatDate,
}: HoldsTabProps): React.ReactElement {
  const { t } = useTranslation()
  const [confirmCancelId, setConfirmCancelId] = useState<number | null>(null)

  function holdStatusLabel(status: string): string {
    if (status === 'ready') return t('account.holdStatusReady')
    if (status === 'pending') return t('account.holdStatusPending')
    return status
  }

  function handleCancelClick(holdId: number) {
    setConfirmCancelId(holdId)
  }

  function handleConfirmCancel(holdId: number) {
    setConfirmCancelId(null)
    onCancel(holdId)
  }

  function handleKeepHold() {
    setConfirmCancelId(null)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('account.myHolds')}</h2>
        <button
          onClick={onRefresh}
          disabled={holdsLoading}
          aria-label={t('account.refreshHolds')}
          className="flex items-center gap-2 px-3 py-2 text-lsc-dark/70 hover:text-lsc-dark transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
        >
          <RefreshCw className={`w-5 h-5 ${holdsLoading ? 'motion-safe:animate-spin' : ''}`} />
          {t('account.refresh')}
        </button>
      </div>

      {holdsLoading ? (
        <div className="flex justify-center py-12" role="status">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
        </div>
      ) : holds.length === 0 ? (
        <div className="text-center py-12">
          <Clock className="w-12 h-12 text-sage/30 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('account.noActiveHolds')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {holds.map(hold => (
            <div key={hold.id} className="p-4 rounded-xl border-2 border-lsc-border bg-lsc-cream dark:bg-earth-800">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-start gap-3">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream text-lg">{hold.item_title}</h3>
                    <span className={`px-3 py-1 text-xs rounded-full font-medium ${
                      hold.status === 'ready' ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300' :
                      hold.status === 'pending' ? 'bg-status-warning-500/20 dark:bg-status-warning-900/30 text-status-warning-600 dark:text-status-warning-300' :
                      'bg-lsc-cream text-lsc-dark/70 dark:bg-earth-700 dark:text-lsc-cream/70'
                    }`}>
                      {holdStatusLabel(hold.status)}
                    </span>
                  </div>
                  {hold.item_author && (
                    <p className="text-lsc-dark/70 text-sm mt-1">{t('account.byAuthor')} {hold.item_author}</p>
                  )}
                  <div className="flex items-center gap-4 mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      <span>{t('account.placed', { date: formatDate(hold.created_at) })}</span>
                    </div>
                    {hold.status === 'pending' && (
                      <div className="flex items-center gap-1">
                        <span>{t('account.positionInQueue', { position: hold.position })}</span>
                      </div>
                    )}
                    {hold.status === 'pending' && hold.estimated_wait_weeks != null && (
                      <div className="flex items-center gap-1 text-lsc-dark/60 dark:text-lsc-cream/60">
                        <Clock className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                        <span>{t('account.holdEstimatedWait', { weeks: hold.estimated_wait_weeks })}</span>
                      </div>
                    )}
                    {hold.status === 'ready' && hold.expires_at && (
                      <div className="flex items-center gap-1 text-status-warning-600 font-medium">
                        <AlertCircle className="w-4 h-4" />
                        <span>{t('account.expires', { date: formatDate(hold.expires_at) })}</span>
                      </div>
                    )}
                    {hold.pickup_branch_name && (
                      <div className="flex items-center gap-1">
                        <MapPin className="w-4 h-4" />
                        <span>{hold.pickup_branch_name}</span>
                      </div>
                    )}
                  </div>
                </div>
                {(hold.status === 'pending' || hold.status === 'ready') && (
                  <div className="ml-4 flex-shrink-0">
                    {confirmCancelId === hold.id ? (
                      <div
                        className="flex flex-col gap-2 p-3 rounded-xl border-2 border-status-danger-300 dark:border-status-danger-700 bg-status-danger-50 dark:bg-status-danger-900/20"
                        role="group"
                        aria-label={t('account.cancelHoldTitle')}
                      >
                        <p className="text-sm font-medium text-status-danger-700 dark:text-status-danger-300">
                          {t('account.cancelHoldConfirmPrompt')}
                        </p>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleConfirmCancel(hold.id)}
                            disabled={cancellingId === hold.id}
                            className="px-3 py-1.5 text-sm bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 flex items-center gap-1"
                          >
                            {cancellingId === hold.id ? (
                              <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" />
                            ) : null}
                            {t('account.yesCancelHold')}
                          </button>
                          <button
                            onClick={handleKeepHold}
                            className="px-3 py-1.5 text-sm bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-100 dark:hover:bg-earth-600 transition-colors border border-lsc-border dark:border-earth-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                          >
                            {t('account.keepHold')}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleCancelClick(hold.id)}
                        disabled={cancellingId === hold.id}
                        className="px-4 py-2 bg-status-danger-600 text-white rounded-xl hover:bg-status-danger-700 transition-colors disabled:opacity-50 flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                      >
                        {cancellingId === hold.id ? (
                          <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                        ) : (
                          t('account.cancel')
                        )}
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
