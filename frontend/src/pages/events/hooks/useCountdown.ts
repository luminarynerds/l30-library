/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'

export interface UpcomingStart {
  kind: 'soon' | 'today' | 'tomorrow'
  time: string
}

// Calm "when does this start" label for events within the next 24 hours.
// Within ~60 minutes: "soon". Otherwise a relative day plus the absolute
// start time ("Today, 4 PM" / "Tomorrow, 11:30 AM"). No countdown math in
// the UI; ticking clocks read as urgency.
function computeUpcomingStart(startTime: string): UpcomingStart | null {
  const now = new Date()
  const eventStart = new Date(startTime)
  const diff = eventStart.getTime() - now.getTime()

  if (diff <= 0 || diff > 24 * 60 * 60 * 1000) return null
  if (diff <= 60 * 60 * 1000) return { kind: 'soon', time: '' }

  const time = eventStart.toLocaleTimeString(undefined, {
    hour: 'numeric',
    ...(eventStart.getMinutes() !== 0 ? { minute: '2-digit' as const } : {}),
  })
  const kind = eventStart.getDate() === now.getDate() ? 'today' : 'tomorrow'
  return { kind, time }
}

export function useCountdown(startTime: string): { upcomingStart: UpcomingStart | null } {
  const [upcomingStart, setUpcomingStart] = useState<UpcomingStart | null>(() => computeUpcomingStart(startTime))

  useEffect(() => {
    setUpcomingStart(computeUpcomingStart(startTime))
    const interval = setInterval(() => setUpcomingStart(computeUpcomingStart(startTime)), 60000)
    return () => clearInterval(interval)
  }, [startTime])

  return { upcomingStart }
}
