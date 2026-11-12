/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo, type RefObject } from 'react'
import { Link } from 'react-router-dom'
import { Calendar } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { getCurrentLocale } from '@/i18n'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import { formatTime } from '@/pages/events/utils/formatters'
import type { Event } from '@/api/api'

interface ThisWeekStripProps {
  events: Event[]
  isLoading?: boolean
  /** Scroll target when an empty day column is clicked. */
  scrollTargetRef?: RefObject<HTMLElement | null>
  /** Rendered inside the merged "Today & this week" band: no own border/heading. */
  embedded?: boolean
}

// Local audience color band — patron-side, not a shared concern with category colors.
function audienceBand(audience: string | null): string {
  const a = (audience ?? '').toLowerCase()
  if (a.includes('kid') || a.includes('child')) return 'border-l-pink-500 dark:border-l-pink-400'
  if (a.includes('teen')) return 'border-l-cyan-500 dark:border-l-cyan-400'
  if (a.includes('senior')) return 'border-l-amber-500 dark:border-l-amber-400'
  if (a.includes('adult')) return 'border-l-indigo-500 dark:border-l-indigo-400'
  return 'border-l-lsc-rose dark:border-l-lsc-rose-light'
}

function startOfLocalDay(d: Date): Date {
  const out = new Date(d)
  out.setHours(0, 0, 0, 0)
  return out
}

function addDays(d: Date, n: number): Date {
  const out = new Date(d)
  out.setDate(out.getDate() + n)
  return out
}

function dayKey(d: Date): string {
  // YYYY-MM-DD in local time (matches DOM anchors)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// Locale-aware day/month names (was hardcoded English arrays)
function weekdayShortName(d: Date): string {
  return new Intl.DateTimeFormat(getCurrentLocale(), { weekday: 'short' }).format(d)
}
function weekdayLongName(d: Date): string {
  return new Intl.DateTimeFormat(getCurrentLocale(), { weekday: 'long' }).format(d)
}
function monthLongName(d: Date): string {
  return new Intl.DateTimeFormat(getCurrentLocale(), { month: 'long' }).format(d)
}

export default function ThisWeekStrip({ events, isLoading, scrollTargetRef, embedded = false }: ThisWeekStripProps): React.ReactElement {
  const { t } = useTranslation()
  const { settings } = useAccessibility()

  const today = useMemo(() => startOfLocalDay(new Date()), [])

  // Today-anchored 7-day window. A Tuesday visitor sees Tue + next 6 days.
  const days = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => addDays(today, i))
  }, [today])

  // Group events by local day key.
  const byDay = useMemo(() => {
    const map = new Map<string, Event[]>()
    for (const e of events) {
      const start = new Date(e.start_time)
      const key = dayKey(startOfLocalDay(start))
      const arr = map.get(key) ?? []
      arr.push(e)
      map.set(key, arr)
    }
    // Sort each day's events by start_time so chip order is chronological.
    for (const arr of map.values()) {
      arr.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
    }
    return map
  }, [events])

  if (isLoading) {
    return (
      <section
        aria-label={t('events.thisWeek.title', 'This week')}
        className={embedded ? '' : 'rounded-xl border-2 border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-800/40 p-3'}
        data-testid="this-week-strip-skeleton"
      >
        <div className="flex md:grid md:grid-cols-7 gap-2 overflow-x-auto snap-x">
          {Array.from({ length: 7 }).map((_, i) => (
            <div
              key={i}
              className="min-w-[140px] md:min-w-0 snap-start rounded-lg bg-lsc-cream dark:bg-earth-800 p-2 animate-pulse h-32"
              aria-hidden="true"
            />
          ))}
        </div>
      </section>
    )
  }

  const scrollToFilters = () => {
    scrollTargetRef?.current?.scrollIntoView({
      behavior: settings.reduceMotion ? 'auto' : 'smooth',
      block: 'start',
    })
  }

  return (
    <section
      aria-label={t('events.thisWeek.title', 'This week')}
      className={embedded ? '' : 'rounded-xl border-2 border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-800/40 p-3'}
    >
      {!embedded && (
        <div className="flex items-center gap-2 mb-3">
          <Calendar aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
          <h2 className="text-sm font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('events.thisWeek.title', 'This week')}
          </h2>
        </div>
      )}
      <div className="flex md:grid md:grid-cols-7 gap-2 overflow-x-auto snap-x pb-1">
        {days.map((d) => {
          const key = dayKey(d)
          const dayEvents = byDay.get(key) ?? []
          const count = dayEvents.length
          const visible = dayEvents.slice(0, 3)
          const overflow = Math.max(0, count - visible.length)
          const weekdayShort = weekdayShortName(d)
          const weekdayLong = weekdayLongName(d)
          const monthLong = monthLongName(d)
          const isToday = key === dayKey(today)
          const ariaLabel = `${weekdayLong} ${monthLong} ${d.getDate()}`

          return (
            <section
              key={key}
              id={`events-day-${key}`}
              aria-label={ariaLabel}
              data-testid={`day-column-${key}`}
              className={`min-w-[140px] md:min-w-0 snap-start rounded-lg p-2 border ${
                isToday
                  ? 'bg-lsc-rose/10 dark:bg-lsc-rose/20 border-lsc-rose/40'
                  : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700'
              } hover:bg-lsc-cream dark:hover:bg-earth-700/60 focus-within:ring-2 focus-within:ring-lsc-rose transition-colors`}
            >
              <div className="flex items-baseline justify-between mb-2">
                <div className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream">
                  <span>{weekdayShort}</span>{' '}
                  <span className="font-bold">{d.getDate()}</span>
                </div>
                {count > 0 && (
                  <span
                    className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-lsc-rose text-white"
                    aria-label={t('events.thisWeek.countLabel', { defaultValue: '{{count}} events', count })}
                  >
                    {count}
                  </span>
                )}
              </div>
              {count === 0 ? (
                scrollTargetRef ? (
                  <button
                    type="button"
                    onClick={scrollToFilters}
                    aria-label={t('events.thisWeek.noEventsBrowse', 'No events. Browse all events.')}
                    className="w-full text-left text-xs text-lsc-dark/60 dark:text-lsc-cream/60 italic rounded px-1 py-0.5 hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  >
                    {t('events.thisWeek.noEvents', 'No events')}
                  </button>
                ) : (
                  <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 italic">
                    {t('events.thisWeek.noEvents', 'No events')}
                  </p>
                )
              ) : (
                <ul className="space-y-1">
                  {visible.map((ev) => (
                    <li key={ev.id}>
                      <Link
                        to={`/events/detail/${ev.id}`}
                        className={`block rounded border-l-2 ${audienceBand(ev.audience)} bg-lsc-cream/60 dark:bg-earth-700/60 px-1.5 py-1 text-[11px] leading-tight text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose`}
                      >
                        <time dateTime={ev.start_time} className="block text-[10px] font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                          {formatTime(ev.start_time)}
                        </time>
                        <span className="block truncate font-medium">{ev.title}</span>
                      </Link>
                    </li>
                  ))}
                  {overflow > 0 && (
                    <li>
                      <a
                        href={`#events-day-${key}`}
                        className="block text-[11px] font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded px-1.5 py-0.5"
                        data-testid={`day-overflow-${key}`}
                      >
                        {t('events.thisWeek.moreCount', { defaultValue: '+{{overflow}} more', overflow })}
                      </a>
                    </li>
                  )}
                </ul>
              )}
            </section>
          )
        })}
      </div>
    </section>
  )
}
