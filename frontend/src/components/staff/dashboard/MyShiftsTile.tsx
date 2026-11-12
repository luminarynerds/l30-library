/**
 * "My Shifts" tile for the staff dashboard.
 *
 * Renders inside a DashboardSection (which supplies the card chrome and title).
 * Backed by GET /fair-scheduling/me/shifts.
 */

import React from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Clock, ArrowLeftRight, PhoneOff, BookOpen } from 'lucide-react'
import { fairSchedulingApi, type MyShift } from '@/api/fair-scheduling-api'
import { getCurrentLocale } from '@/i18n'

const TILE_LIMIT = 4

/**
 * Library's IANA timezone. Shift times from the backend are naive (no offset),
 * so we anchor all comparisons to this zone. Single-library deployment --
 * if L30 ever goes multi-branch across zones, the backend should return
 * tz-aware ISO strings instead.
 */
const LIBRARY_TIMEZONE = 'America/New_York'

/** Current wall-clock time in the library's timezone. */
const libraryNow = (): Date => {
  const s = new Date().toLocaleString(getCurrentLocale(), { timeZone: LIBRARY_TIMEZONE })
  return new Date(s)
}

/** Parse a naive date + HH:MM:SS into a Date anchored to the library timezone. */
const libraryDate = (isoDate: string, hms: string): Date => {
  const raw = new Date(`${isoDate}T${hms}`)
  const s = raw.toLocaleString(getCurrentLocale(), { timeZone: LIBRARY_TIMEZONE })
  return new Date(s)
}

const formatTime = (hms: string): string => {
  const [hStr, mStr] = hms.split(':')
  const h = Number(hStr)
  const m = Number(mStr)
  if (Number.isNaN(h) || Number.isNaN(m)) return hms
  const ampm = h >= 12 ? 'PM' : 'AM'
  const hour12 = h % 12 === 0 ? 12 : h % 12
  return `${hour12}:${m.toString().padStart(2, '0')} ${ampm}`
}

const dayLabel = (isoDate: string): string => {
  const d = libraryDate(isoDate, '00:00:00')
  const today = libraryNow()
  today.setHours(0, 0, 0, 0)
  const dayMs = 24 * 60 * 60 * 1000
  const diff = Math.round((d.getTime() - today.getTime()) / dayMs)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
}

const isShiftLive = (shift: MyShift): boolean => {
  const now = libraryNow()
  const start = libraryDate(shift.shift_date, shift.scheduled_start)
  const end = libraryDate(shift.shift_date, shift.scheduled_end)
  return now >= start && now <= end
}

const startsSoonLabel = (shift: MyShift): string | null => {
  const now = libraryNow()
  const start = libraryDate(shift.shift_date, shift.scheduled_start)
  const diffMin = Math.round((start.getTime() - now.getTime()) / 60000)
  if (diffMin <= 0 || diffMin > 180) return null
  if (diffMin < 60) return `starts in ${diffMin}m`
  const h = Math.floor(diffMin / 60)
  const m = diffMin % 60
  return m === 0 ? `starts in ${h}h` : `starts in ${h}h ${m}m`
}

const MyShiftsTile: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['fair-scheduling', 'me', 'shifts'],
    queryFn: () => fairSchedulingApi.getMyShifts({ days_ahead: 14, include_today: true }),
    refetchInterval: 5 * 60 * 1000,
    staleTime: 4 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm py-2">
        <BookOpen aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-breathe" />
        Loading your schedule…
      </div>
    )
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        Couldn't load your schedule right now.
      </p>
    )
  }

  const shifts = data.shifts.slice(0, TILE_LIMIT)

  if (shifts.length === 0) {
    return (
      <div className="text-center py-6">
        <Clock aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-dark/40 dark:text-lsc-cream/40 opacity-50" />
        <p className="mt-2 font-medium text-lsc-dark dark:text-lsc-cream">No upcoming shifts</p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Nothing scheduled in the next 2 weeks.
        </p>
        <Link
          to="/staff/fair-scheduling"
          className="mt-3 inline-block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
        >
          View full schedule
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <ul className="space-y-3">
        {shifts.map((shift) => {
          const live = isShiftLive(shift)
          const soon = !live ? startsSoonLabel(shift) : null
          return (
            <li
              key={shift.shift_id}
              className={`rounded-lg border p-3 ${
                live
                  ? 'border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10'
                  : 'border-lsc-border dark:border-earth-700'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {dayLabel(shift.shift_date)}
                    </span>
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {formatTime(shift.scheduled_start)} – {formatTime(shift.scheduled_end)}
                    </span>
                    {live && (
                      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-lsc-rose text-white">
                        On now
                      </span>
                    )}
                    {soon && (
                      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/40 dark:text-status-warning-200">
                        {soon}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 flex items-center gap-2 flex-wrap">
                    <span className="capitalize">{shift.shift_type.replace('_', ' ')}</span>
                    <span aria-hidden="true">·</span>
                    <span>{shift.scheduled_hours}h</span>
                    {shift.has_open_swap && (
                      <span className="text-lsc-rose dark:text-lsc-rose-light font-medium">
                        · open swap
                      </span>
                    )}
                    {shift.has_open_callout && (
                      <span className="text-status-warning-700 dark:text-status-warning-300 font-medium">
                        · callout open
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Link
                    to={`/staff/shift-swap?shift_id=${shift.shift_id}`}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-earth-700"
                    aria-label="Swap this shift"
                  >
                    <ArrowLeftRight aria-hidden="true" className="w-3.5 h-3.5" />
                    Swap
                  </Link>
                  <Link
                    to={`/staff/fair-scheduling/call-outs?shift_id=${shift.shift_id}`}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
                    aria-label="Call out from this shift"
                  >
                    <PhoneOff aria-hidden="true" className="w-3.5 h-3.5" />
                    Call out
                  </Link>
                </div>
              </div>
            </li>
          )
        })}
      </ul>
      <div className="flex justify-end">
        <Link
          to="/staff/fair-scheduling"
          className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
        >
          View full schedule
        </Link>
      </div>
    </div>
  )
}

export default MyShiftsTile
