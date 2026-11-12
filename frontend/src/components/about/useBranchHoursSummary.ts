/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { getBranchHours, type BranchHours } from '@/api/branch-api'

const DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] as const
const SHORT_DAY: Record<string, string> = {
  Monday: 'Mon',
  Tuesday: 'Tue',
  Wednesday: 'Wed',
  Thursday: 'Thu',
  Friday: 'Fri',
  Saturday: 'Sat',
  Sunday: 'Sun',
}

function formatTime(time: string): string {
  const parts = time.split(':').map(Number)
  const hour = parts[0] ?? 0
  const min = parts[1] ?? 0
  const period = hour >= 12 ? 'pm' : 'am'
  const h12 = hour % 12 || 12
  return min === 0 ? `${h12}${period}` : `${h12}:${String(min).padStart(2, '0')}${period}`
}

function dayKey(h: BranchHours): string {
  if (h.is_closed || !h.open_time || !h.close_time) return 'closed'
  return `${formatTime(h.open_time)}-${formatTime(h.close_time)}`
}

export function formatHoursSummary(hours: BranchHours[]): string {
  if (!hours || hours.length === 0) return 'Hours not available'

  const byDay = new Map<string, BranchHours>()
  for (const h of hours) byDay.set(h.day_of_week, h)

  const ordered = DAY_ORDER.map((d) => byDay.get(d)).filter((h): h is BranchHours => Boolean(h))
  if (ordered.length === 0) return 'Hours not available'

  const groups: Array<{ start: string; end: string; key: string }> = []
  for (const h of ordered) {
    const key = dayKey(h)
    const last = groups[groups.length - 1]
    if (last && last.key === key) {
      last.end = h.day_of_week
    } else {
      groups.push({ start: h.day_of_week, end: h.day_of_week, key })
    }
  }

  return groups
    .map((g) => {
      const range = g.start === g.end ? SHORT_DAY[g.start] : `${SHORT_DAY[g.start]}-${SHORT_DAY[g.end]}`
      return g.key === 'closed' ? `${range} closed` : `${range} ${g.key}`
    })
    .join(', ')
}

export function useBranchHoursSummary(branchId: number, enabled = true): {
  summary: string | null
  isLoading: boolean
  isError: boolean
} {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['branch-hours', branchId],
    queryFn: () => getBranchHours(branchId),
    staleTime: 10 * 60 * 1000,
    enabled,
  })

  return {
    summary: data ? formatHoursSummary(data) : null,
    isLoading,
    isError,
  }
}
