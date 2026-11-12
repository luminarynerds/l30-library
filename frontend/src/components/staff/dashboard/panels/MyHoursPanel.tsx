/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { Clock } from "lucide-react"
import { getCurrentLocale } from '@/i18n'
import {
  getTimesheetToday,
  getTimesheetSummary,
  TimesheetDayResponse,
  TimesheetSummaryResponse,
} from "@/api/domains/staff/staff-presence-api"

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const

// Local date components, not toISOString: the backend buckets shift_date in
// library-local time, and the UTC date is already tomorrow after 8pm Eastern.
function localDateISO(dt: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`
}

export function getWeekBounds(today: Date): { monday: string; sunday: string } {
  const d = new Date(today)
  const day = d.getDay()
  const diffToMon = day === 0 ? -6 : 1 - day
  const monday = new Date(d)
  monday.setDate(d.getDate() + diffToMon)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  return { monday: localDateISO(monday), sunday: localDateISO(sunday) }
}

function fmtTime(iso: string | null): string {
  if (!iso) return "--"
  return new Date(iso).toLocaleTimeString(getCurrentLocale(), {
    hour: "numeric",
    minute: "2-digit",
  })
}

function fmtHours(h: number | null): string {
  if (h == null) return "--"
  return h.toFixed(1)
}

function statusColor(status: string): string {
  if (status === "completed") return "text-status-success-600 dark:text-status-success-400"
  if (status === "in_progress" || status === "incomplete") return "text-status-warning-600 dark:text-status-warning-400"
  return "text-lsc-dark/40 dark:text-lsc-cream/40"
}

function statusLabel(status: string): string {
  if (status === "in_progress") return "In progress"
  if (status === "completed") return "Completed"
  if (status === "incomplete") return "Missing clock-out"
  return "Not started"
}

function StatusBadge({ status }: { status: string }) {
  const bg =
    status === "completed" || status === "in_progress"
      ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300"
      : "bg-earth-200 dark:bg-earth-700 text-lsc-dark/50 dark:text-lsc-cream/50"
  return (
    <span className={`text-[11px] px-1.5 py-0.5 rounded-full ${bg}`}>
      {statusLabel(status)}
    </span>
  )
}

interface MyHoursPanelProps {
  compact?: boolean
}

export default function MyHoursPanel({ compact = false }: MyHoursPanelProps) {
  const [today, setToday] = useState<TimesheetDayResponse | null>(null)
  const [summary, setSummary] = useState<TimesheetSummaryResponse | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    const now = new Date()
    const { monday, sunday } = getWeekBounds(now)
    Promise.all([getTimesheetToday(), getTimesheetSummary(monday, sunday)])
      .then(([t, s]) => {
        setToday(t)
        setSummary(s)
      })
      .catch(() => setError(true))
  }, [])

  if (compact) {
    if (error) {
      return (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-3 shadow-sm">
          <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" aria-hidden="true" />
            Hours tracking unavailable
          </p>
        </div>
      )
    }
    if (!today) {
      return (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-3 shadow-sm animate-pulse">
          <div className="h-3 bg-earth-200 dark:bg-earth-700 rounded w-1/2" />
        </div>
      )
    }
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-3 shadow-sm">
        <p className="text-sm text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-lsc-dark/60 dark:text-lsc-cream/60" aria-hidden="true" />
          <span>
            My hours today:{" "}
            <span className="font-medium">{fmtHours(today.total_worked_hours)} hrs</span>
          </span>
          <span className={`text-xs ${statusColor(today.status)}`}>
            ({statusLabel(today.status).toLowerCase()})
          </span>
        </p>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 flex items-center gap-1.5 mb-2">
          <Clock className="w-3.5 h-3.5" aria-hidden="true" />
          My hours
        </p>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
          <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
            Hours tracking unavailable
          </p>
        </div>
      </div>
    )
  }

  if (!today || !summary) {
    return (
      <div>
        <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 flex items-center gap-1.5 mb-2">
          <Clock className="w-3.5 h-3.5" aria-hidden="true" />
          My hours
        </p>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm animate-pulse">
          <div className="h-3 bg-earth-200 dark:bg-earth-700 rounded w-1/3" />
        </div>
      </div>
    )
  }

  const todayDateStr = localDateISO(new Date())
  // A past day still "in_progress" is a missed clock-out, not 500 worked
  // hours; the post-guard backend reports these as "incomplete".
  const isMissedClockOut = (day: TimesheetDayResponse) =>
    day.status === "incomplete" ||
    (day.status === "in_progress" && day.shift_date !== todayDateStr)
  const hasMissedClockOut = summary.days.some(isMissedClockOut)

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 flex items-center gap-1.5 mb-2">
        <Clock className="w-3.5 h-3.5" aria-hidden="true" />
        My hours
      </p>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm divide-y divide-lsc-border dark:divide-earth-700">
        <div className="p-4 space-y-2">
          <p className="text-xs font-medium uppercase tracking-wider text-lsc-dark/40 dark:text-lsc-cream/40">
            Today
          </p>
          <div className="flex items-center justify-between">
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/70">
              Clocked in: <span className="text-lsc-dark dark:text-lsc-cream">{fmtTime(today.clock_in)}</span>
            </p>
            <StatusBadge status={today.status} />
          </div>
          {today.breaks.length > 0 && (
            <div className="space-y-0.5">
              {today.breaks.map((b, i) => (
                <p key={i} className="text-xs text-lsc-dark/60 dark:text-lsc-cream/70">
                  Break: {fmtTime(b.start)} - {fmtTime(b.end)}
                  {b.duration_minutes != null && (
                    <span className="text-lsc-dark/50 dark:text-lsc-cream/50"> ({b.duration_minutes} min)</span>
                  )}
                </p>
              ))}
            </div>
          )}
          <div className="flex items-center justify-between text-xs">
            <p className="text-lsc-dark/60 dark:text-lsc-cream/70">
              Worked{today.status === "in_progress" ? " so far" : ""}:{" "}
              <span className="text-lsc-dark dark:text-lsc-cream">{fmtHours(today.total_worked_hours)} hrs</span>
            </p>
            {today.scheduled_hours != null && (
              <p className="text-lsc-dark/50 dark:text-lsc-cream/50">
                Scheduled: {fmtHours(today.scheduled_hours)} hrs
              </p>
            )}
          </div>
        </div>

        <div className="p-4 space-y-2">
          <p className="text-xs font-medium uppercase tracking-wider text-lsc-dark/40 dark:text-lsc-cream/40">
            This week
          </p>
          <div className="space-y-1">
            {summary.days.map((day) => {
              const dt = new Date(day.shift_date + "T00:00:00")
              const dayName = DAY_NAMES[dt.getDay()]
              const isToday = day.shift_date === todayDateStr
              const missedClockOut = isMissedClockOut(day)
              const color = isToday || missedClockOut
                ? "text-status-warning-600 dark:text-status-warning-400"
                : day.status === "completed"
                  ? "text-status-success-600 dark:text-status-success-400"
                  : "text-lsc-dark/40 dark:text-lsc-cream/40"

              let label: string
              if (isToday && day.status === "in_progress") {
                label = "(today - in progress)"
              } else if (day.status === "completed") {
                label = `${fmtHours(day.total_worked_hours)} hrs`
              } else if (day.status === "not_started" && day.scheduled_hours) {
                label = "(scheduled)"
              } else if (day.status === "not_started") {
                label = "--"
              } else {
                label = `${fmtHours(day.total_worked_hours)} hrs`
              }

              const scheduled =
                day.scheduled_hours != null && day.status === "completed"
                  ? ` (of ${fmtHours(day.scheduled_hours)})`
                  : ""

              return (
                <div key={day.shift_date} className={`flex items-center justify-between text-xs ${color}`}>
                  <span className="w-8 font-medium">{dayName}</span>
                  {missedClockOut ? (
                    <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300">
                      Missing clock-out
                    </span>
                  ) : (
                    <span>
                      {label}
                      {scheduled && (
                        <span className="text-lsc-dark/40 dark:text-lsc-cream/40">{scheduled}</span>
                      )}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
          {hasMissedClockOut && (
            <p className="text-[11px] text-status-warning-700 dark:text-status-warning-300">
              A shift is missing a clock-out, so these totals may be off. Check the alert
              next to the Clock in button to get it fixed.
            </p>
          )}
          <div className="pt-1 border-t border-lsc-border dark:border-earth-700 flex items-center justify-between text-xs">
            <span className="font-medium text-lsc-dark/60 dark:text-lsc-cream/60">Total</span>
            <span className="text-lsc-dark dark:text-lsc-cream">
              {fmtHours(summary.total_worked_hours)} / {fmtHours(summary.total_scheduled_hours)} hrs
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
