/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * LibraryStatusBanner Component
 *
 * Displays library open/closed status with today's hours.
 * Shows below the main header.
 * Fetches hours from the API so staff-managed changes take effect immediately.
 */

import { Clock, AlertCircle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from '../i18n/I18nContext'
import { clsx } from '@/utils/helpers'
import { getIsOpen, getLibraryHours } from '@/api/domains/content/homepage-content-api'

interface LibraryStatusBannerProps {
  className?: string
  announcement?: string | null
}

function formatTimestamp(time: string): string {
  const parts = time.split(':').map(Number)
  const hour = parts[0] ?? 0
  const min = parts[1] ?? 0
  const period = hour >= 12 ? 'PM' : 'AM'
  const h12 = hour % 12 || 12
  return min === 0 ? `${h12} ${period}` : `${h12}:${String(min).padStart(2, '0')} ${period}`
}

export default function LibraryStatusBanner({
  className,
  announcement
}: LibraryStatusBannerProps): React.ReactElement {
  const { t } = useTranslation()

  const { data: openStatus } = useQuery({
    queryKey: ['library-is-open'],
    queryFn: getIsOpen,
    staleTime: 60_000,
    refetchInterval: 60_000,
  })

  const { data: hoursData } = useQuery({
    queryKey: ['library-hours-weekly'],
    queryFn: getLibraryHours,
    staleTime: 300_000,
  })

  const isOpen = openStatus?.is_open ?? false
  const statusText = isOpen ? t('home.hours.openNow') : t('home.hours.closed')

  // Derive today's hours from API data
  const todayHours = (() => {
    if (!hoursData?.weekly) return null
    const dayIndex = new Date().getDay()
    const today = hoursData.weekly.find((d) => d.day_of_week === dayIndex)
    if (!today || today.is_closed) return t('home.hours.closed')
    if (!today.open_time || !today.close_time) return null
    return `${formatTimestamp(today.open_time)} - ${formatTimestamp(today.close_time)}`
  })()

  // Don't render until we have data to avoid flash of wrong state
  if (!openStatus || !todayHours) return <></>

  return (
    <section
      aria-label={t('home.hours.statusRegion')}
      className={clsx(
        'bg-lsc-cream/95 dark:bg-earth-900/95 border-b border-lsc-border dark:border-earth-700',
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between py-1.5 text-sm">
          {/* Status and hours */}
          <div className="flex items-center gap-2 sm:gap-4">
            <div className="flex items-center gap-2">
              <span
                className={clsx(
                  'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
                  isOpen
                    ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400'
                    : 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400'
                )}
              >
                <span
                  className={clsx(
                    'w-1.5 h-1.5 rounded-full',
                    isOpen ? 'bg-status-success-500' : 'bg-status-danger-500'
                  )}
                  aria-hidden="true"
                />
                {statusText}
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-lsc-dark/70 dark:text-lsc-cream/70">
              <Clock aria-hidden="true" className="w-3.5 h-3.5 hidden sm:block" />
              <span className="text-xs sm:text-sm">
                <span className="hidden sm:inline">{t('dates.today')}: </span>
                {todayHours}
              </span>
            </div>
          </div>

          {announcement && (
            <div className="flex items-center gap-1.5 text-lsc-rose dark:text-lsc-rose-light">
              <AlertCircle aria-hidden="true" className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="truncate max-w-[120px] sm:max-w-xs text-xs sm:text-sm">{announcement}</span>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
