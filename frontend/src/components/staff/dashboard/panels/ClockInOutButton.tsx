/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Clock, LogOut, Loader2, AlertTriangle } from "lucide-react"
import { ApiError } from "@/lib/api-client"
import {
  updatePresenceStatus,
  getMyOpenShifts,
  getTimesheetToday,
  type OpenShiftEntry,
  type TimesheetDayResponse,
} from "@/api/domains/staff/staff-presence-api"
import { useElapsed, fmtElapsed } from "./useElapsed"

function fmtClock(iso: string | null): string | null {
  if (!iso) return null
  const d = new Date(iso)
  if (isNaN(d.getTime())) return null
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
}

function fmtDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" })
}

export default function ClockInOutButton({ onPunch }: { onPunch?: () => void }) {
  const [today, setToday] = useState<TimesheetDayResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [openShifts, setOpenShifts] = useState<OpenShiftEntry[]>([])

  const refreshTimesheet = () => getTimesheetToday().then(setToday)

  useEffect(() => {
    Promise.all([
      refreshTimesheet(),
      getMyOpenShifts(7).then(setOpenShifts),
    ])
      .catch(() => setErr("Couldn't load shift status"))
      .finally(() => setLoading(false))
    // getMyPresence kept only as a no-op warm path is dropped: timesheet is source of truth.
  }, [])

  // Timesheet is the source of truth for clock state, not presence.
  const isClockedIn = today?.status === "in_progress"

  const handleToggle = async () => {
    if (submitting) return
    setSubmitting(true)
    setErr(null)
    try {
      await updatePresenceStatus(isClockedIn ? "off_duty" : "available")
      const fresh = await getTimesheetToday()
      setToday(fresh)
      getMyOpenShifts(7).then(setOpenShifts).catch(() => {})
      onPunch?.()
      // Reconcile: presence may have flipped while the punch failed to record.
      if (!isClockedIn && fresh.status !== "in_progress") {
        setErr("Clock-in didn't record — try again, or ask a manager to fix it.")
      }
    } catch (e) {
      setErr(e instanceof ApiError && e.status < 500 ? e.detail : "Couldn't update shift status")
    } finally {
      setSubmitting(false)
    }
  }

  const startedLabel = fmtClock(today?.clock_in ?? null)
  const elapsed = useElapsed(isClockedIn ? (today?.clock_in ?? null) : null)

  return (
    <div className="space-y-3">
      {openShifts.length > 0 && (
        <div
          role="alert"
          className="flex items-start gap-3 bg-status-warning-50 dark:bg-status-warning-900/30 border border-status-warning-200 dark:border-status-warning-700 rounded-xl p-3"
        >
          <AlertTriangle
            className="w-5 h-5 text-status-warning-700 dark:text-status-warning-300 shrink-0 mt-0.5"
            aria-hidden="true"
          />
          <div className="min-w-0 text-sm text-lsc-dark dark:text-lsc-cream">
            <p className="font-medium">
              You didn't clock out
              {openShifts.length === 1 ? ` on ${fmtDate(openShifts[0]!.shift_date)}` : ` on ${openShifts.length} recent shifts`}
              .
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Ask a manager to fix it on the{" "}
              <Link to="/staff/admin/timesheets" className="underline hover:text-lsc-rose">
                timesheet editor
              </Link>
              . Payroll will fall back to scheduled hours until then.
            </p>
            {openShifts.length > 1 && (
              <ul className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 list-disc list-inside">
                {openShifts.map(o => (
                  <li key={o.shift_date}>
                    {fmtDate(o.shift_date)} -- clocked in at {fmtClock(o.clock_in)}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between gap-3 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4">
        <div className="min-w-0" aria-live="polite">
          <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60">
            Shift
          </p>
          <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream truncate">
            {loading
              ? "Loading..."
              : isClockedIn
                ? startedLabel
                  ? `Clocked in at ${startedLabel}`
                  : "Clocked in"
                : "Not clocked in"}
          </p>
          {isClockedIn && elapsed !== null && (
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-0.5 tabular-nums">
              On the clock: {fmtElapsed(elapsed)}
            </p>
          )}
          {err && (
            <p role="status" aria-live="assertive" className="text-xs text-status-danger-600 mt-1">
              {err}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={handleToggle}
          disabled={loading || submitting}
          aria-label={isClockedIn ? "Clock out" : "Clock in"}
          className={
            "shrink-0 inline-flex items-center gap-2 px-4 py-3 text-base font-semibold rounded-xl shadow-sm transition-all " +
            "motion-safe:hover:scale-[1.03] motion-safe:active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed " +
            (isClockedIn
              ? "bg-status-danger-600 hover:bg-status-danger-700 text-lsc-white"
              : "bg-lsc-rose hover:bg-lsc-rose/90 text-lsc-white")
          }
        >
          {submitting ? (
            <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />
          ) : isClockedIn ? (
            <LogOut className="w-5 h-5" aria-hidden="true" />
          ) : (
            <Clock className="w-5 h-5" aria-hidden="true" />
          )}
          {isClockedIn ? "Clock out" : "Clock in"}
        </button>
      </div>
    </div>
  )
}
