/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Clock, Volume2, MapPin } from 'lucide-react'
import { getLabMap, type LabMapStation } from '@/api/computer-lab-map-api'
import { useTranslation } from '@/i18n/I18nContext'
import { useBranding } from '@/contexts/BrandingContext'
import type { IsOpenResponse } from '@/api/domains/content/homepage-content-api'

function isCountedActive(s: LabMapStation): boolean {
  return s.status !== 'maintenance' && s.status !== 'offline'
}

type BusynessLevel = 'open_quiet' | 'open_busy' | 'open_moderate' | 'closed' | 'unknown'

export function deriveBusyness(
  openStatus: IsOpenResponse | null | undefined,
  free: number | null,
  total: number | null,
): BusynessLevel {
  if (!openStatus?.is_open) return 'closed'
  if (free === null || total === null || total === 0) return 'unknown'
  const ratio = free / total
  if (ratio >= 0.6) return 'open_quiet'
  if (ratio <= 0.25) return 'open_busy'
  return 'open_moderate'
}

interface Props {
  openStatus: IsOpenResponse | null | undefined
}

export default function PlanYourVisit({ openStatus }: Props): React.ReactElement | null {
  const { t } = useTranslation()
  const branding = useBranding()

  const { data: labData } = useQuery({
    queryKey: ['computer-lab-map'],
    queryFn: getLabMap,
    staleTime: 25_000,
    refetchInterval: 30_000,
  })

  const { free, total } = useMemo(() => {
    if (!labData || !Array.isArray(labData.stations)) return { free: null, total: null }
    const active = labData.stations.filter(isCountedActive)
    return {
      free: active.filter(s => s.status === 'available').length,
      total: labData.stations.length,
    }
  }, [labData])

  const busyness = deriveBusyness(openStatus, free, total)

  const hasConfig =
    Boolean(branding.quiet_hours) ||
    Boolean(branding.sensory_friendly_times) ||
    Boolean(branding.low_stim_seating)

  if (busyness === 'closed' && !hasConfig) return null

  const busynessLabel: string = (() => {
    switch (busyness) {
      case 'open_quiet':
        return t('home.planVisit.busyness.quiet', 'Computers are wide open right now')
      case 'open_moderate':
        return t('home.planVisit.busyness.moderate', "It's a bit busier than usual")
      case 'open_busy':
        return t('home.planVisit.busyness.busy', 'Most computers are in use right now')
      case 'closed':
        return t('home.planVisit.busyness.closed', "We're closed right now")
      case 'unknown':
      default:
        return t('home.planVisit.busyness.unknown', 'Check the computer lab for current availability')
    }
  })()

  return (
    <div className="h-full">
      <div className="h-full rounded-xl border border-earth-200 dark:border-earth-700 bg-lsc-cream dark:bg-earth-900 p-6 md:p-8 space-y-6">

        <h2
          id="plan-visit-heading"
          className="font-mono text-xs uppercase tracking-widest text-earth-700 dark:text-earth-400"
        >
          {t('home.planVisit.heading', 'Plan your visit')}
        </h2>

        <div className="space-y-1">
          <p className="font-serif text-2xl md:text-3xl font-semibold text-lsc-dark dark:text-lsc-cream leading-tight">
            {busynessLabel}
          </p>
          {(busyness === 'open_quiet' || busyness === 'open_moderate' || busyness === 'open_busy') && (
            <p className="text-sm text-earth-700 dark:text-earth-400">
              {t('home.planVisit.busynessSource', 'Based on computer lab availability')}
            </p>
          )}
        </div>

        {(branding.quiet_hours || branding.sensory_friendly_times || branding.low_stim_seating) && (
          <dl className="space-y-5 border-t border-earth-200 dark:border-earth-700 pt-6">

            {branding.quiet_hours && (
              <div className="flex gap-4">
                <dt className="flex-shrink-0">
                  <span className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-sage-100 dark:bg-sage-900/30">
                    <Clock className="w-4 h-4 text-sage-600 dark:text-sage-400" aria-hidden="true" />
                  </span>
                </dt>
                <dd className="space-y-0.5">
                  <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    {t('home.planVisit.quietHours', 'Quiet hours')}
                  </p>
                  <p className="text-sm text-earth-700 dark:text-earth-300">
                    {branding.quiet_hours}
                  </p>
                </dd>
              </div>
            )}

            {branding.sensory_friendly_times && (
              <div className="flex gap-4">
                <dt className="flex-shrink-0">
                  <span className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20">
                    <Volume2 className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                  </span>
                </dt>
                <dd className="space-y-0.5">
                  <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    {t('home.planVisit.sensoryTimes', 'Sensory-friendly times')}
                  </p>
                  <p className="text-sm text-earth-700 dark:text-earth-300">
                    {branding.sensory_friendly_times}
                  </p>
                </dd>
              </div>
            )}

            {branding.low_stim_seating && (
              <div className="flex gap-4">
                <dt className="flex-shrink-0">
                  <span className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-earth-100 dark:bg-earth-800/40">
                    <MapPin className="w-4 h-4 text-earth-600 dark:text-earth-300" aria-hidden="true" />
                  </span>
                </dt>
                <dd className="space-y-0.5">
                  <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    {t('home.planVisit.lowStimSeating', 'Low-stimulation seating')}
                  </p>
                  <p className="text-sm text-earth-700 dark:text-earth-300">
                    {branding.low_stim_seating}
                  </p>
                </dd>
              </div>
            )}

          </dl>
        )}

      </div>
    </div>
  )
}
