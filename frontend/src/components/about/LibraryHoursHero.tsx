/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * LibraryHoursHero
 *
 * Hero block for the public About page surfacing the two most-asked questions:
 * "When are you open?" and "How do I get a card?". Stateless except for the
 * library-hours query (shared cache with LibraryStatusBanner).
 */

import { Clock, MapPin, Phone, BookOpen, CreditCard, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getLibraryHours, getIsOpen, type DayHours } from '@/api/domains/content/homepage-content-api'
import { useBranding } from '@/contexts/BrandingContext'

interface LibraryHoursHeroProps {
  /** Override the hours summary string (e.g., for orgs without staffed hours data) */
  hoursSummary?: string
  /** Override the address shown beneath the CTAs */
  address?: string
  /** Override the phone number shown beneath the CTAs */
  phone?: string
}

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function formatTime(time: string | null): string {
  if (!time) return ''
  const [hStr, mStr] = time.split(':')
  const hour = Number(hStr ?? 0)
  const min = Number(mStr ?? 0)
  const period = hour >= 12 ? 'pm' : 'am'
  const h12 = hour % 12 || 12
  return min === 0 ? `${h12}${period}` : `${h12}:${String(min).padStart(2, '0')}${period}`
}

function formatRange(day: DayHours): string | null {
  if (day.is_closed || !day.open_time || !day.close_time) return null
  return `${formatTime(day.open_time)}-${formatTime(day.close_time)}`
}

function summarizeWeek(weekly: DayHours[]): string | null {
  // Order Mon..Sun for display
  const order = [1, 2, 3, 4, 5, 6, 0]
  const days = order
    .map((dow) => weekly.find((d) => d.day_of_week === dow))
    .filter((d): d is DayHours => Boolean(d))
  if (days.length === 0) return null

  const segments: string[] = []
  let i = 0
  while (i < days.length) {
    const startDay = days[i]
    if (!startDay) { i++; continue }
    const range = formatRange(startDay)
    if (!range) { i++; continue }
    let j = i
    while (j + 1 < days.length) {
      const nextDay = days[j + 1]
      if (!nextDay || formatRange(nextDay) !== range) break
      j++
    }
    const endDay = days[j]
    if (!endDay) { i = j + 1; continue }
    const startLabel = DAY_NAMES[startDay.day_of_week]
    const endLabel = DAY_NAMES[endDay.day_of_week]
    segments.push(j === i ? `${startLabel} ${range}` : `${startLabel}-${endLabel} ${range}`)
    i = j + 1
  }
  return segments.length > 0 ? segments.join(', ') : null
}

function todayHoursFromWeekly(weekly: DayHours[]): string | null {
  const today = weekly.find((d) => d.day_of_week === new Date().getDay())
  if (!today) return null
  if (today.is_closed) return 'Closed today'
  const range = formatRange(today)
  return range ? `Today: ${range}` : null
}

export default function LibraryHoursHero({
  hoursSummary,
  address,
  phone,
}: LibraryHoursHeroProps): React.ReactElement {
  const branding = useBranding()

  const { data: hoursData } = useQuery({
    queryKey: ['library-hours-weekly'],
    queryFn: getLibraryHours,
    staleTime: 300_000,
  })

  const { data: openStatus } = useQuery({
    queryKey: ['library-is-open'],
    queryFn: getIsOpen,
    staleTime: 60_000,
    refetchInterval: 60_000,
  })

  const liveSummary = hoursData?.weekly ? summarizeWeek(hoursData.weekly) : null
  const liveToday = hoursData?.weekly ? todayHoursFromWeekly(hoursData.weekly) : null

  // TODO(sam): replace with real hours data source if /library-hours is empty in production
  const summary =
    hoursSummary ?? liveSummary ?? 'Mon-Thu 9am-9pm, Fri-Sat 9am-6pm, Sun 12pm-5pm'

  const isOpen = openStatus?.is_open
  const todayLine = liveToday

  // TODO(sam): replace placeholder address when branding.address_line1 is unset
  const composedBrandingAddress = [
    branding.address_line1,
    branding.address_line2,
    [branding.city, branding.state].filter(Boolean).join(', '),
    branding.zip_code,
  ]
    .filter(Boolean)
    .join(', ')
  const resolvedAddress =
    address ?? (composedBrandingAddress || null)

  const resolvedPhone = phone ?? branding.phone ?? ''

  return (
    <section
      aria-label="Library hours and getting started"
      className="py-10 md:py-12 bg-gradient-to-br from-lsc-cream to-sage-50 dark:from-lsc-dark dark:to-earth-900 border-b border-lsc-border dark:border-earth-700"
    >
      <div className="container mx-auto px-4 max-w-5xl">
        <div className="grid md:grid-cols-2 gap-6 md:gap-10 items-start">
          {/* Hours */}
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="flex-shrink-0 w-10 h-10 bg-lsc-rose/10 rounded-full flex items-center justify-center">
                <Clock className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              </div>
              <h2 className="text-xl md:text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                When we're open
              </h2>
            </div>
            {todayLine && (
              <p className="ml-[52px] mb-1 text-sm">
                <span
                  className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
                    isOpen
                      ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400'
                      : 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400'
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isOpen ? 'bg-status-success-500' : 'bg-status-danger-500'
                    }`}
                    aria-hidden="true"
                  />
                  {isOpen ? 'Open now' : 'Closed'}
                </span>{' '}
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{todayLine}</span>
              </p>
            )}
            <p className="ml-[52px] text-lsc-dark/80 dark:text-lsc-cream/80 leading-relaxed">
              {summary}
            </p>
            {resolvedAddress && (
              <p className="ml-[52px] mt-3 text-sm text-lsc-dark/60 dark:text-lsc-cream/60 flex items-start gap-2">
                <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
                <span>{resolvedAddress}</span>
              </p>
            )}
            {resolvedPhone && (
              <p className="ml-[52px] mt-1 text-sm text-lsc-dark/60 dark:text-lsc-cream/60 flex items-center gap-2">
                <Phone className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                <a
                  href={`tel:${resolvedPhone.replace(/\D/g, '')}`}
                  className="hover:text-lsc-rose hover:underline transition-colors"
                >
                  {resolvedPhone}
                </a>
              </p>
            )}
          </div>

          {/* CTAs */}
          <div className="flex flex-col gap-3">
            <Link
              to="/card-application"
              className="group inline-flex items-center justify-between gap-3 px-5 py-4 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-xl transition-colors shadow-sm"
            >
              <span className="flex items-center gap-3">
                <CreditCard className="w-5 h-5" aria-hidden="true" />
                <span>
                  <span className="block text-base font-semibold">Get a library card</span>
                  <span className="block text-xs text-white">Free for anyone in our service area</span>
                </span>
              </span>
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
            </Link>
            <Link
              to="/catalog"
              className="group inline-flex items-center justify-between gap-3 px-5 py-4 bg-lsc-white dark:bg-earth-700 hover:bg-sage-50 dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream font-medium rounded-xl border border-lsc-border dark:border-earth-700 transition-colors"
            >
              <span className="flex items-center gap-3">
                <BookOpen className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                <span>
                  <span className="block text-base font-semibold">Find a book</span>
                  <span className="block text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                    Search the catalog and place holds
                  </span>
                </span>
              </span>
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
