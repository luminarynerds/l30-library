/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { Coffee, HelpCircle, Loader2, LogOut } from 'lucide-react'
import toast from 'react-hot-toast'
import { ApiError } from '@/lib/api-client'
import {
  getMyPresence,
  getTimesheetToday,
  updatePresenceStatus,
  requestHelp,
  type StaffStatus,
} from '@/api/domains/staff/staff-presence-api'

export default function ShelverActions() {
  const [status, setStatus] = useState<StaffStatus>('available')
  const [loading, setLoading] = useState<string | null>(null)
  // Timesheet is the source of truth for clock state, not presence.
  const [todayStatus, setTodayStatus] = useState<string | null>(null)

  const refreshToday = () =>
    getTimesheetToday()
      .then((t) => setTodayStatus(t.status))
      .catch(() => {})

  useEffect(() => {
    getMyPresence()
      .then((res) => setStatus(res.status))
      .catch(() => {})
    refreshToday()
  }, [])

  const onBreak = status === 'on_break'
  const clockedIn = todayStatus === 'in_progress'

  const handleBreak = async () => {
    const target: StaffStatus = onBreak ? 'available' : 'on_break'
    setLoading('break')
    try {
      const res = await updatePresenceStatus(target)
      setStatus(res.status)
      toast.success(onBreak ? 'Welcome back!' : 'Break started. Take your time.')
    } catch {
      toast.error('Could not update status. Try again.')
    } finally {
      refreshToday()
      setLoading(null)
    }
  }

  const handleHelp = async () => {
    setLoading('help')
    try {
      const res = await requestHelp()
      if (res.notified_count > 1) {
        toast(`Help request sent to ${res.notified_count} supervisor(s).`, { icon: '✉️' })
      } else {
        toast('Your supervisor has been notified.', { icon: '✉️' })
      }
    } catch {
      toast.error('Could not send help request. Try again.')
    } finally {
      setLoading(null)
    }
  }

  const handleEndShift = async () => {
    setLoading('end')
    try {
      const res = await updatePresenceStatus('off_duty')
      setStatus(res.status)
      toast.success('Shift ended. Great work today!')
    } catch (e) {
      toast.error(
        e instanceof ApiError && e.status < 500 && e.detail
          ? e.detail
          : 'Could not end shift. Try again.',
      )
    } finally {
      // Reconcile with the timesheet either way: a successful clock-out
      // disables the button, and a 409 means another tab beat us to it.
      refreshToday()
      setLoading(null)
    }
  }

  return (
    <div className="flex flex-wrap gap-2 pt-2">
      <button
        onClick={handleBreak}
        disabled={loading !== null}
        className={`flex items-center gap-2 px-4 py-2.5 text-sm rounded-xl motion-safe:hover:scale-[1.03] motion-safe:active:scale-[0.98] transition-all disabled:opacity-50 ${
          onBreak
            ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400'
            : 'bg-lsc-cream/70 dark:bg-earth-700/70 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700'
        }`}
      >
        <Coffee className="w-4 h-4" aria-hidden="true" />
        {onBreak ? "I'm back" : "I'm taking my break"}
      </button>
      <button
        onClick={handleHelp}
        disabled={loading !== null}
        className="flex items-center gap-2 px-4 py-2.5 text-sm rounded-xl bg-lsc-cream/70 dark:bg-earth-700/70 text-lsc-dark/70 dark:text-lsc-cream/70 motion-safe:hover:scale-[1.03] motion-safe:active:scale-[0.98] hover:bg-lsc-cream dark:hover:bg-earth-700 transition-all disabled:opacity-50"
      >
        <HelpCircle className="w-4 h-4" aria-hidden="true" />
        Need help with something
      </button>
      <button
        onClick={handleEndShift}
        disabled={loading !== null || !clockedIn}
        className="flex items-center gap-2 px-4 py-2.5 text-sm rounded-xl bg-lsc-cream/70 dark:bg-earth-700/70 text-lsc-dark/70 dark:text-lsc-cream/70 motion-safe:hover:scale-[1.03] motion-safe:active:scale-[0.98] hover:bg-lsc-cream dark:hover:bg-earth-700 transition-all disabled:opacity-50"
      >
        {loading === 'end' ? (
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
        ) : (
          <LogOut className="w-4 h-4" aria-hidden="true" />
        )}
        End shift
      </button>
    </div>
  )
}
