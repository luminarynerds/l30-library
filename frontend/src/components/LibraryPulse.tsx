/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  MapPin, Phone, AlertCircle, Info, X,
  ArrowRight, Calendar
} from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { useAuth } from '@/contexts/AuthContext'
import { API_BASE } from '@/api/types'
import api from '@/lib/api-client'
import { logger } from '@/utils/logger'
import type { Announcement } from '@/api/domains/notifications/announcements-api'
import type { DayHours, HoursOverride } from '@/api/domains/content/homepage-content-api'



interface PulseData {
  checkouts_today: number
  next_event?: { id: number; title: string; start_time: string } | null
}

interface LibraryPulseProps {
  openStatus: { is_open: boolean; opens_at: string | null; closes_at: string | null } | null
  mainBranch: any
  todayHoursLabel: string | null
  announcements: Announcement[] | null
  upcomingEvent?: { id: number; title: string; start_time: string } | null
  weekly?: DayHours[] | null
  overrides?: HoursOverride[] | null
}

// Next day (including later today) the library opens, honoring date overrides.
// Returns null when nothing in the next week is open or hours are unknown.
export function nextOpening(
  weekly: DayHours[] | null | undefined,
  overrides: HoursOverride[] | null | undefined,
  now: Date,
): { isToday: boolean; dayOfWeek: number; time: string } | null {
  if (!weekly || weekly.length === 0) return null
  const pad = (n: number): string => String(n).padStart(2, '0')
  const nowHM = `${pad(now.getHours())}:${pad(now.getMinutes())}`
  for (let i = 0; i < 8; i++) {
    const d = new Date(now.getTime() + i * 86_400_000)
    const dow = d.getDay()
    const dateStr = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
    const eff = overrides?.find((o) => o.date === dateStr) ?? weekly.find((w) => w.day_of_week === dow)
    if (!eff || eff.is_closed || !eff.open_time) continue
    // Today only counts if it hasn't opened yet; otherwise we're past close.
    if (i === 0) {
      if (nowHM < eff.open_time) return { isToday: true, dayOfWeek: dow, time: eff.open_time }
      continue
    }
    return { isToday: false, dayOfWeek: dow, time: eff.open_time }
  }
  return null
}

// day_of_week is 0=Sunday .. 6=Saturday (matches JS Date.getDay()).
const WEEKDAY_KEYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
// Display the week Monday-first, the way a posted library sign reads.
const WEEK_ORDER = [1, 2, 3, 4, 5, 6, 0]

function formatCountdown(startTime: string): string | null {
  const diff = new Date(startTime).getTime() - Date.now()
  if (diff <= 0) return null
  const totalMinutes = Math.floor(diff / 60000)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours > 24) return `in ${Math.floor(hours / 24)}d`
  if (hours > 0) return `in ${hours}h`
  return `in ${minutes}m`
}

function formatTo12Hour(time: string): string {
  const parts = time.split(':').map(Number)
  const h = parts[0] ?? 0
  const m = parts[1] ?? 0
  const suffix = h >= 12 ? 'PM' : 'AM'
  const hour12 = h % 12 || 12
  return m === 0 ? `${hour12} ${suffix}` : `${hour12}:${String(m).padStart(2, '0')} ${suffix}`
}

export default function LibraryPulse({
  openStatus,
  mainBranch,
  todayHoursLabel,
  announcements,
  upcomingEvent,
  weekly,
  overrides,
}: LibraryPulseProps) {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth()

  const [dismissedIds, setDismissedIds] = useState<number[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('dismissed-announcements') || '[]')
    } catch { return [] }
  })

  const { data: pulseData } = useQuery<PulseData | null>({
    queryKey: ['community-pulse'],
    queryFn: () => api.get(`${API_BASE}/stats/community-pulse`).catch((err) => {
      logger.error('Failed to fetch community pulse:', err)
      return null
    }) as Promise<PulseData | null>,
    refetchInterval: 60_000,
  })

  const dismissAnnouncement = (id: number) => {
    const updated = [...dismissedIds, id]
    setDismissedIds(updated)
    localStorage.setItem('dismissed-announcements', JSON.stringify(updated))
  }

  const activeAnnouncements = announcements?.filter(
    (a) => !a.ends_at || new Date(a.ends_at) > new Date()
  )?.filter((a) => {
    if (a.target_audience === 'staff' && !isAuthenticated) return false
    return true
  })?.filter((a) => !dismissedIds.includes(a.id))

  const urgentAnnouncements = activeAnnouncements?.filter(a => a.priority !== 'normal') ?? []
  const normalAnnouncements = activeAnnouncements?.filter(a => a.priority === 'normal') ?? []

  const event = upcomingEvent ?? pulseData?.next_event
  const countdown = event ? formatCountdown(event.start_time) : null
  const open = openStatus?.is_open ?? false
  const todayIndex = new Date().getDay()

  // Warm status sub-line, in the home hero's voice. When closed, name the next
  // opening (day + time) from the schedule; fall back to openStatus, then generic.
  const upcoming = open ? null : nextOpening(weekly, overrides, new Date())
  const subline = open
    ? (openStatus?.closes_at
        ? t('home.visitUs.openSubline', { time: formatTo12Hour(openStatus.closes_at) })
        : t('home.visitUs.openSublineNoTime'))
    : upcoming
        ? (upcoming.isToday
            ? t('home.visitUs.closedSubline', { time: formatTo12Hour(upcoming.time) })
            : t('home.visitUs.closedSublineDay', {
                day: t(`footer.days.${WEEKDAY_KEYS[upcoming.dayOfWeek]}`),
                time: formatTo12Hour(upcoming.time),
              }))
        : (openStatus?.opens_at
            ? t('home.visitUs.closedSubline', { time: formatTo12Hour(openStatus.opens_at) })
            : t('home.visitUs.closedGeneric'))

  // `label` holds the day's display name (e.g. "Monday"), not an hours string,
  // so the value column is always the open/close range (or closed).
  const dayRange = (d: DayHours): string => {
    if (d.is_closed) return t('home.visitUs.closedDay')
    if (d.open_time && d.close_time) return `${formatTo12Hour(d.open_time)} - ${formatTo12Hour(d.close_time)}`
    return t('home.visitUs.closedDay')
  }

  const hasWeek = Array.isArray(weekly) && weekly.length > 0
  const hasSidebar = urgentAnnouncements.length > 0 || normalAnnouncements.length > 0 || Boolean(event && countdown)

  return (
    <section className="grid grid-cols-1 lg:grid-cols-3 gap-6" aria-label={t('home.communityPulse.label')}>
      {/* Visit Us — the front-door sign. Status leads; hours + directions live here. */}
      <div className={hasSidebar ? 'lg:col-span-2' : 'lg:col-span-3'}>
        <div className="h-full grid grid-cols-1 sm:grid-cols-[1.15fr_0.85fr] rounded-xl border border-lsc-border dark:border-earth-700/50 overflow-hidden shadow-soft-sm bg-lsc-white dark:bg-earth-800/40">

          {/* The sign: open/closed state as the hero */}
          <div className={`p-6 sm:p-8 ${open ? 'bg-forest-500/10 dark:bg-forest-900/20' : 'bg-status-warning-50 dark:bg-status-warning-900/20'} transition-colors duration-500`}>
            <h2 className="font-mono text-[11px] uppercase tracking-[0.18em] text-earth-700 dark:text-earth-400 mb-5">
              {t('home.visitUs.title')}
            </h2>

            <div className="flex items-center gap-3">
              <span className="relative flex h-3 w-3 flex-shrink-0" aria-hidden="true">
                {open && (
                  <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-forest-500 opacity-60"></span>
                )}
                <span className={`relative inline-flex rounded-full h-3 w-3 ${open ? 'bg-forest-600' : 'bg-status-warning-500'}`}></span>
              </span>
              <p className={`font-serif text-3xl md:text-4xl leading-none ${open ? 'text-forest-700 dark:text-forest-400' : 'text-status-warning-700 dark:text-status-warning-400'}`}>
                {!openStatus ? t('navigation.hoursAndLocations') : open ? t('home.heartbeat.open') : t('home.heartbeat.closed')}
              </p>
            </div>

            <p className="mt-3 text-[15px] text-lsc-dark dark:text-lsc-cream">
              {openStatus && subline}
            </p>

            {hasWeek && (
              <table
                className="w-full mt-6 pt-5 border-t border-earth-200 dark:border-earth-700/50 text-sm"
                aria-label={t('home.visitUs.weekHours')}
              >
                <tbody className="font-mono tabular-nums">
                  {WEEK_ORDER.map((dow) => {
                    const d = weekly!.find((x) => x.day_of_week === dow)
                    if (!d) return null
                    const isToday = dow === todayIndex
                    return (
                      <tr
                        key={dow}
                        className={isToday
                          ? 'font-semibold text-lsc-dark dark:text-lsc-cream'
                          : 'text-earth-700 dark:text-earth-300'}
                      >
                        <th scope="row" className="relative text-left font-normal py-1 pl-3">
                          {isToday && (
                            <span
                              className={`absolute left-0 top-1/2 -translate-y-1/2 w-1 h-4 rounded-full ${open ? 'bg-forest-500' : 'bg-status-warning-500'}`}
                              aria-hidden="true"
                            ></span>
                          )}
                          {isToday ? t('home.visitUs.today') : t(`footer.days.${WEEKDAY_KEYS[dow]}`)}
                        </th>
                        <td className="text-right py-1">{dayRange(d)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}

            {!hasWeek && todayHoursLabel && (
              <p className="mt-4 text-sm text-earth-700 dark:text-earth-400">{todayHoursLabel}</p>
            )}
          </div>

          {/* Getting there: address, directions, phone */}
          <div className="p-6 sm:p-8 flex flex-col gap-6">
            {mainBranch?.address_line1 && (
              <div>
                <p className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.14em] text-earth-700 dark:text-earth-400 mb-1.5">
                  <MapPin className="w-3.5 h-3.5" aria-hidden="true" />
                  {t('home.visitUs.findUs')}
                </p>
                <address className="not-italic text-sm text-lsc-dark dark:text-lsc-cream leading-relaxed">
                  {mainBranch.address_line1}<br />
                  {mainBranch.address_line2 && <>{mainBranch.address_line2}<br /></>}
                  {[mainBranch.city, mainBranch.state, mainBranch.zip_code].filter(Boolean).join(', ')}
                </address>
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([mainBranch.address_line1, mainBranch.address_line2, mainBranch.city, mainBranch.state, mainBranch.zip_code].filter(Boolean).join(', '))}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group inline-flex items-center gap-1.5 mt-2 text-sm font-bold text-sage-700 dark:text-lsc-rose hover:text-sage-800 transition-colors focus-visible:ring-2 focus-visible:ring-sage-500 focus-visible:outline-none rounded"
                >
                  {t('home.visitUs.getDirections')}
                  <ArrowRight className="w-4 h-4 motion-safe:group-hover:translate-x-1 motion-safe:transition-transform" aria-hidden="true" />
                </a>
              </div>
            )}

            {mainBranch?.phone && (
              <div>
                <p className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.14em] text-earth-700 dark:text-earth-400 mb-1.5">
                  <Phone className="w-3.5 h-3.5" aria-hidden="true" />
                  {t('home.visitUs.callDesk')}
                </p>
                <a href={`tel:${mainBranch.phone.replace(/[^+\d]/g, '')}`} className="text-sm text-lsc-dark dark:text-lsc-cream border-b border-earth-100 dark:border-earth-700/50 hover:border-sage-500 transition-colors">
                  {mainBranch.phone}
                </a>
              </div>
            )}

            <div className="flex-1" />

            <Link
              to="/branches"
              className="inline-flex items-center gap-1.5 pt-4 border-t border-earth-100 dark:border-earth-700/50 text-[13px] text-earth-700 dark:text-earth-400 hover:text-sage-600 dark:hover:text-lsc-rose transition-colors focus-visible:ring-2 focus-visible:ring-sage-500 focus-visible:outline-none rounded"
            >
              {t('home.visitUs.allHours')}
              <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </div>

      {/* Sidebar: announcements + next event (hours now live in the card) */}
      {hasSidebar && (
        <div className="lg:col-span-1 space-y-4">
          {/* Urgent / important announcements */}
          {urgentAnnouncements.map((announcement) => (
            <div
              key={announcement.id}
              className="flex items-center gap-3 px-4 py-3 rounded-xl bg-status-danger-50 dark:bg-status-danger-900/30 border border-status-danger-200 dark:border-status-danger-800/50 motion-safe:transition-all duration-300 motion-safe:hover:translate-x-1 text-lsc-dark dark:text-lsc-cream"
            >
              <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0" aria-hidden="true" />
              <Link
                to="/announcements"
                className="min-w-0 flex-1 no-underline text-lsc-dark dark:text-lsc-cream"
              >
                <span className="text-sm font-semibold">{announcement.title}</span>
              </Link>
              <button
                onClick={() => dismissAnnouncement(announcement.id)}
                className="flex-shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center rounded hover:bg-black/5 dark:hover:bg-white/10 transition-colors focus-visible:ring-2 focus-visible:ring-sage-500 focus-visible:outline-none"
                aria-label={`Dismiss ${announcement.title}`}
              >
                <X className="w-4 h-4 text-lsc-dark/40 dark:text-lsc-cream/40" aria-hidden="true" />
              </button>
            </div>
          ))}

          {(normalAnnouncements.length > 0 || (event && countdown)) && (
            <div className="bg-lsc-white dark:bg-earth-800/40 rounded-xl border border-lsc-border dark:border-earth-700/50 p-5 sm:p-6 shadow-soft-sm space-y-3">
              {normalAnnouncements.length > 0 && (
                <div className="space-y-3">
                  {normalAnnouncements.map(announcement => (
                    <div key={announcement.id} className="flex items-start gap-3 group">
                      <Info className="w-4 h-4 mt-0.5 text-sage-600 dark:text-lsc-rose flex-shrink-0" aria-hidden="true" />
                      <Link to="/announcements" className="flex-1 text-sm text-earth-700 dark:text-earth-300 hover:text-lsc-rose transition-colors line-clamp-1">
                        {announcement.title}
                      </Link>
                      <button
                        onClick={() => dismissAnnouncement(announcement.id)}
                        className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity focus-visible:ring-2 focus-visible:ring-sage-500 focus-visible:outline-none"
                        aria-label={`Dismiss ${announcement.title}`}
                      >
                        <X className="w-3 h-3 text-earth-600" aria-hidden="true" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {event && countdown && (
                <Link
                  to={`/events/detail/${event.id}`}
                  className={`flex items-center justify-between p-4 rounded-xl bg-lsc-white dark:bg-earth-900/40 border border-earth-100 dark:border-earth-700/50 group hover:border-sage-400 transition-all duration-300 ${normalAnnouncements.length > 0 ? 'mt-1' : ''}`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Calendar className="w-4 h-4 text-sage-600 flex-shrink-0" aria-hidden="true" />
                    <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream line-clamp-1">
                      {event.title} <span className="text-earth-700 dark:text-earth-300 font-normal ml-1">{countdown}</span>
                    </span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-earth-600 group-hover:text-sage-600 motion-safe:group-hover:translate-x-1 transition-all duration-300 flex-shrink-0" aria-hidden="true" />
                </Link>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
