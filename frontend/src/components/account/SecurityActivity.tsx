/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Security Activity Component
 *
 * Shows recent security events from audit log.
 * Color-coded by status, with device info and pagination.
 */
import React, { useState, useEffect } from 'react'
import { Loader2, ChevronDown, CheckCircle2, XCircle, AlertTriangle, ArrowRightLeft } from 'lucide-react'
import { getSecurityActivity, type SecurityActivityItem } from '@/api/account-security-api'
import { useNeurodivergentUX } from '@/hooks/useNeurodivergentUX'
import { useTranslation} from '@/i18n'

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const seconds = Math.max(0, Math.floor((now.getTime() - date.getTime()) / 1000))

  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`
  return date.toLocaleDateString()
}

const statusConfigNormal = {
  success: { icon: CheckCircle2, color: 'text-status-success-600 dark:text-status-success-400', bg: 'bg-status-success-50 dark:bg-status-success-900/20' },
  failed: { icon: XCircle, color: 'text-status-danger-600 dark:text-status-danger-400', bg: 'bg-status-danger-50 dark:bg-status-danger-900/20' },
  blocked: { icon: AlertTriangle, color: 'text-status-danger-600 dark:text-status-danger-400', bg: 'bg-status-danger-50 dark:bg-status-danger-900/20' },
  change: { icon: ArrowRightLeft, color: 'text-status-warning-600 dark:text-status-warning-400', bg: 'bg-status-warning-50 dark:bg-status-warning-900/20' },
}

const statusConfigMuted = {
  success: { icon: CheckCircle2, color: 'text-lsc-dark/70 dark:text-lsc-cream/70', bg: 'bg-lsc-cream dark:bg-earth-800/30' },
  failed: { icon: XCircle, color: 'text-lsc-dark/70 dark:text-lsc-cream/70', bg: 'bg-lsc-cream dark:bg-earth-800/30' },
  blocked: { icon: AlertTriangle, color: 'text-lsc-dark/70 dark:text-lsc-cream/70', bg: 'bg-lsc-cream dark:bg-earth-800/30' },
  change: { icon: ArrowRightLeft, color: 'text-lsc-dark/70 dark:text-lsc-cream/70', bg: 'bg-lsc-cream dark:bg-earth-800/30' },
}

export const SecurityActivity: React.FC = () => {
  const { simplifiedView, quietMode } = useNeurodivergentUX()
  const { t } = useTranslation()
  const [items, setItems] = useState<SecurityActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const fetchActivity = async (pageNum: number, append: boolean = false) => {
    try {
      setError(false)
      const res = await getSecurityActivity(pageNum, 10)
      setItems(prev => append ? [...prev, ...res.items] : res.items)
      setTotal(res.total)
      setPage(pageNum)
    } catch {
      setError(true)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- on-mount data fetch; fetchActivity resets state synchronously before its await
    fetchActivity(1).finally(() => setLoading(false))
  }, [])

  const handleLoadMore = async () => {
    setLoadingMore(true)
    await fetchActivity(page + 1, true)
    setLoadingMore(false)
  }

  const hasMore = items.length < total

  return (
    <div>
      {loading ? (
        <div className="flex justify-center py-8" role="status" aria-label={t('aria.account.loadingSecurityActivity')}>
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/60" aria-hidden="true" />
        </div>
      ) : error ? (
        <div className="text-center py-6" role="alert">
          <p className="text-sm text-status-danger-600 dark:text-status-danger-400">Unable to load activity.</p>
          <button type="button" onClick={() => { setLoading(true); fetchActivity(1).finally(() => setLoading(false)) }} className="text-sm text-lsc-rose hover:underline mt-2">Retry</button>
        </div>
      ) : items.length === 0 ? (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-6">
          {simplifiedView ? 'No activity yet.' : t('accountSecurity.activity.noActivity')}
        </p>
      ) : (
        <div aria-live="polite" aria-relevant="additions">
          <div className="space-y-2">
            {items.map((item, i) => {
              const statusConfig = quietMode ? statusConfigMuted : statusConfigNormal
              const config = statusConfig[item.status] || statusConfig.change
              const Icon = config.icon

              return (
                <div
                  key={`${item.action}-${item.timestamp}-${i}`}
                  className={`flex items-start gap-3 p-3 rounded-lg ${config.bg}`}
                >
                  <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${config.color}`} aria-hidden="true" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {item.action_label}
                    </p>
                    <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">
                      <span>
                        {timeAgo(item.timestamp)}
                        <span className="sr-only"> ({new Date(item.timestamp).toLocaleString()})</span>
                      </span>
                      {item.device && <span>{item.device}</span>}
                      {item.ip_address && <span>{item.ip_address}</span>}
                    </div>
                  </div>
                </div>
              )
            })}

            {hasMore && (
              <button
                type="button"
                onClick={handleLoadMore}
                disabled={loadingMore}
                aria-label={loadingMore ? 'Loading more activity...' : 'Show more activity'}
                className="w-full flex items-center justify-center gap-2 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
              >
                {loadingMore ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4" aria-hidden="true" />
                    {t('accountSecurity.activity.showMore')}
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
