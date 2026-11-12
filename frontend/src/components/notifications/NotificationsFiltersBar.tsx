/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Filter, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { clsx } from '../../utils/helpers'
import { useTranslation } from '@/i18n'
import { typeFilterOptions, readFilterOptions } from './notifications-data'
import type { TypeFilter, ReadFilter } from './notifications-data'

interface NotificationsFiltersBarProps {
  typeFilter: TypeFilter
  setTypeFilter: (v: TypeFilter) => void
  readFilter: ReadFilter
  setReadFilter: (v: ReadFilter) => void
  loading: boolean
  onRefresh: () => void
  totalCount: number
  unreadCount: number
}

export function NotificationsFiltersBar({
  typeFilter,
  setTypeFilter,
  readFilter,
  setReadFilter,
  loading,
  onRefresh,
  totalCount,
  unreadCount,
}: NotificationsFiltersBarProps): React.ReactElement {
  const { t } = useTranslation()

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-4 mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
            <label htmlFor="type-filter" className="sr-only">Filter by type</label>
            <select
              id="type-filter"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as TypeFilter)}
              className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              {typeFilterOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <label htmlFor="read-filter" className="sr-only">{t('notifications.filterByReadStatus2')}</label>
          <select
            id="read-filter"
            value={readFilter}
            onChange={(e) => setReadFilter(e.target.value as ReadFilter)}
            className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          >
            {readFilterOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>

          <Button variant="secondary"
            onClick={onRefresh}
            disabled={loading}
            aria-label={t('aria.notifications.refreshNotifications')}
            title="Refresh (R)"
          >
            <RefreshCw className={clsx('w-4 h-4', loading && 'motion-safe:animate-spin')} />
            <span className="text-sm">Refresh</span>
          </Button>
        </div>

        <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <span>{totalCount} total</span>
          {unreadCount > 0 && (
            <>
              <span aria-hidden="true">·</span>
              <span className="text-lsc-rose font-medium">{unreadCount} unread</span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
