/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'
import toast from 'react-hot-toast'
import { SessionTimer } from './SessionTimer'
import { useComputerSessions } from './useComputerSessions'
import { t } from '@/i18n'

export function ActiveSession() {
  const { currentSession, loading, fetchCurrentSession, extendSession, endSession } = useComputerSessions()

  useEffect(() => { fetchCurrentSession() }, [fetchCurrentSession])

  if (loading) return <div className="motion-safe:animate-pulse h-24 bg-earth-100 dark:bg-earth-800 rounded-lg" />
  if (!currentSession) return null

  // Bridge Reservation shape (from API) to the timer's expected shape.
  // actual_start_time is null until patron checks in, so fall back to
  // reserved_start_time — otherwise getProgressPercentage() divides by NaN.
  const mappedSession = {
    ...currentSession,
    session_start_time: currentSession.actual_start_time ?? currentSession.reserved_start_time,
    session_end_time: currentSession.extended_until ?? currentSession.reserved_end_time,
  }

  const handleExtend = async () => {
    try {
      await extendSession(30)
      toast.success(t('toast.computers.sessionExtended'))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.computers.failedToExtend'))
    }
  }

  const handleLogoff = async () => {
    try {
      await endSession()
      toast.success(t('toast.computers.sessionEnded'))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.computers.failedToEnd'))
    }
  }

  return (
    <SessionTimer
      session={mappedSession}
      onExtensionRequest={handleExtend}
      onLogoff={handleLogoff}
    />
  )
}
