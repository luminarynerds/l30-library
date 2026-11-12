/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight } from 'lucide-react'
import { getLabMap, type LabMapStation } from '@/api/computer-lab-map-api'
import { useTranslation } from '@/i18n/I18nContext'

function minutesUntil(iso: string | null): number | null {
  if (!iso) return null
  const ms = new Date(iso).getTime() - Date.now()
  if (Number.isNaN(ms)) return null
  return Math.max(0, Math.round(ms / 60_000))
}

function isCountedActive(s: LabMapStation): boolean {
  // Treat maintenance/offline as "not in service" — don't include in availability totals.
  return s.status !== 'maintenance' && s.status !== 'offline'
}

export default function ComputerLabStatus(): React.ReactElement | null {
  const { t } = useTranslation()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['computer-lab-map'],
    queryFn: getLabMap,
    refetchInterval: 30_000,
    staleTime: 25_000,
  })

  const summary = useMemo(() => {
    if (!data || !Array.isArray(data.stations) || data.stations.length === 0) return null
    const inService = data.stations.filter(isCountedActive)
    // Denominator is the full fleet so out-of-service machines aren't hidden.
    // Numerator is what's bookable RIGHT NOW (available, in service).
    const fleetTotal = data.stations.length
    const inServiceCount = inService.length
    const free = inService.filter(s => s.status === 'available').length
    const busy = inServiceCount - free
    const outOfService = fleetTotal - inServiceCount
    const nextFreeMin = busy === 0
      ? null
      : (() => {
          const candidates = inService
            .filter(s => s.status !== 'available')
            .map(s => minutesUntil(s.available_at))
            .filter((m): m is number => m !== null)
          return candidates.length ? Math.min(...candidates) : null
        })()
    return { fleetTotal, inServiceCount, free, busy, nextFreeMin, outOfService }
  }, [data])

  if (isLoading || isError || !summary) return null

  const { fleetTotal, inServiceCount, free, busy, nextFreeMin, outOfService } = summary

  const headline =
    inServiceCount === 0
      ? t('computerLab.allOutOfService')
      : t('computerLab.available', { free: String(free), total: String(fleetTotal) })
  const subtitle =
    nextFreeMin !== null && busy > 0
      ? t('computerLab.wait', { minutes: String(nextFreeMin) })
      : null

  return (
    <div className="h-full">
      <div className="h-full rounded-xl border border-earth-200 dark:border-earth-700 bg-lsc-white dark:bg-earth-900 p-6 md:p-8 space-y-6">
        <h2
          id="computer-lab-status-heading"
          className="font-mono text-xs uppercase tracking-[0.25em] text-earth-700 dark:text-earth-400"
        >
          {t('computerLab.title')}
        </h2>
        <div className="space-y-2">
          <p className="font-serif text-2xl md:text-3xl font-semibold text-lsc-dark dark:text-lsc-cream leading-tight">
            {headline}
          </p>
          {subtitle && (
            <p className="text-base md:text-lg text-earth-600 dark:text-earth-400">
              {subtitle}
            </p>
          )}
          {outOfService > 0 && (
            <p className="text-sm text-earth-700 dark:text-earth-300">
              {t('computerLab.outOfService', { count: String(outOfService) })}
            </p>
          )}
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6">
          <Link
            to="/computers"
            className="inline-flex items-center gap-2 text-sm font-bold text-sage-700 dark:text-lsc-rose hover:text-sage-800 transition-colors"
          >
            {t('computerLab.cta')}
            <ArrowRight className="w-4 h-4" />
          </Link>
          <p className="text-sm text-earth-700 dark:text-earth-400">
            {t('computerLab.printingNote')}{' '}
            <Link
              to="/guides/wireless-printing"
              className="font-bold text-sage-700 dark:text-lsc-rose hover:text-sage-800 underline-offset-2 hover:underline transition-colors"
            >
              {t('computerLab.printingLink')}
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
