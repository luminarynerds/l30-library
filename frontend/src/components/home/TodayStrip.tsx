/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { Clock, Monitor, Calendar, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getLabMap, type LabMapStation } from '@/api/computer-lab-map-api'
import type { Event } from '@/api/events-api'
import type { IsOpenResponse } from '@/api/domains/content/homepage-content-api'
import { useTranslation } from '@/i18n/I18nContext'

interface TodayStripProps {
  openStatus: IsOpenResponse | null
  events: Event[] | null
  todayHoursLabel: string | null
}

function formatTo12Hour(time: string): string {
  // Expected "HH:MM" or "HH:MM:SS" — defensive.
  const parts = time.split(':').map(Number)
  const h = parts[0] ?? 0
  const m = parts[1] ?? 0
  const suffix = h >= 12 ? 'PM' : 'AM'
  const hour12 = h % 12 || 12
  return m === 0 ? `${hour12} ${suffix}` : `${hour12}:${String(m).padStart(2, '0')} ${suffix}`
}

function formatEventTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

function isToday(iso: string): boolean {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return false
  return d.toDateString() === new Date().toDateString()
}

function isCountedActive(s: LabMapStation): boolean {
  return s.status !== 'maintenance' && s.status !== 'offline'
}

interface Pill {
  key: string
  icon: React.ReactNode
  text: string
  serif?: boolean
}

export default function TodayStrip({
  openStatus,
  events,
  todayHoursLabel,
}: TodayStripProps): React.ReactElement | null {
  const { t } = useTranslation()

  // Shares query key with ComputerLabStatus — react-query dedupes the request.
  const { data: labData } = useQuery({
    queryKey: ['computer-lab-map'],
    queryFn: getLabMap,
    refetchInterval: 30_000,
    staleTime: 25_000,
  })

  const pills: Pill[] = []

  // --- Open / closed pill ---
  if (openStatus?.is_open && openStatus.closes_at) {
    pills.push({
      key: 'open',
      icon: <Clock className="w-4 h-4" aria-hidden="true" />,
      text: t('home.today.comeOnIn', 'Come on in'),
      serif: true,
    })
  } else if (openStatus && !openStatus.is_open && openStatus.opens_at) {
    pills.push({
      key: 'opens-at',
      icon: <Clock className="w-4 h-4" aria-hidden="true" />,
      text: t('home.today.backAt', { time: formatTo12Hour(openStatus.opens_at) }),
      serif: true,
    })
  } else if (todayHoursLabel) {
    pills.push({
      key: 'closed',
      icon: <Clock className="w-4 h-4" aria-hidden="true" />,
      text: t('home.today.closedToday', 'Closed today'),
    })
  }

  // --- Computers pill (only meaningful when library is open) ---
  if (openStatus?.is_open && labData && labData.stations.length > 0) {
    const inService = labData.stations.filter(isCountedActive)
    const free = inService.filter((s) => s.status === 'available').length
    if (inService.length > 0) {
      pills.push({
        key: 'computers',
        icon: <Monitor className="w-4 h-4" aria-hidden="true" />,
        text:
          free > 0
            ? t('home.today.computersFree', { count: String(free) })
            : t('home.today.computersAllBusy', 'All computers in use'),
      })
    }
  }

  // --- Next 1-2 events today ---
  const todaysEvents = (events ?? [])
    .filter((e) => isToday(e.start_time) && new Date(e.start_time).getTime() > Date.now())
    .slice(0, 2)
  todaysEvents.forEach((event) => {
    pills.push({
      key: `event-${event.id}`,
      icon: <Calendar className="w-4 h-4" aria-hidden="true" />,
      text: t('home.today.eventAt', {
        title: event.title,
        time: formatEventTime(event.start_time),
      }),
    })
  })

  if (pills.length === 0) return null

  return (
    <section
      aria-labelledby="today-strip-heading"
      className="max-w-5xl mx-auto px-6"
    >
      <div className="rounded-xl border border-earth-200 dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-5 py-5 shadow-soft-sm md:px-8 md:py-6">
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2 mb-3">
          <h2
            id="today-strip-heading"
            className="font-mono text-xs uppercase tracking-[0.25em] text-earth-700 dark:text-earth-400"
          >
            {t('home.today.title', 'Today at the library')}
          </h2>
          <Link
            to="/hours"
            className="inline-flex min-h-[44px] items-center text-sm font-bold text-sage-700 hover:text-sage-800 dark:text-lsc-rose focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500 rounded"
          >
            {t('home.visitUs.title')}
          </Link>
        </div>
        <ul className="flex flex-wrap gap-2 md:gap-3" role="list">
          {pills.map((pill) => (
            <li
              key={pill.key}
              className="inline-flex items-center gap-2 rounded-full bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 px-3 py-1.5 text-sm text-lsc-dark dark:text-lsc-cream"
            >
              <span className="text-sage-700 dark:text-lsc-rose">{pill.icon}</span>
              <span className={pill.serif ? 'font-serif italic' : undefined}>{pill.text}</span>
            </li>
          ))}
        </ul>
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 border-t border-earth-100 dark:border-earth-700/50 pt-4">
          <Link to="/events" className="inline-flex min-h-[44px] items-center gap-1.5 text-sm font-bold text-sage-700 hover:text-sage-800 dark:text-lsc-rose focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500 rounded">
            {t('home.today.viewEvents', 'View events')} <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
          <Link to="/rooms" className="inline-flex min-h-[44px] items-center gap-1.5 text-sm font-bold text-sage-700 hover:text-sage-800 dark:text-lsc-rose focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500 rounded">
            {t('home.today.bookSpace', 'Book a space')} <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
          <Link to="/computers" className="inline-flex min-h-[44px] items-center gap-1.5 text-sm font-bold text-sage-700 hover:text-sage-800 dark:text-lsc-rose focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500 rounded">
            {t('home.today.reserveComputer', 'Reserve a computer')} <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      </div>
    </section>
  )
}
