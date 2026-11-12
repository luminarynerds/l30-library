/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { Event } from '@/api/api'

export interface SeriesGroup {
  series_id: string
  series_name: string
  events: Event[]
}

// 'linear' — a flat, chronological, de-duplicated list with the promotional
// rails suppressed. A per-page view choice;
// distinct from the global EssentialsMode calm-mode product.
export type ViewMode = 'list' | 'calendar-month' | 'calendar-week' | 'agenda' | 'linear'

export function isToday(dateStr: string): boolean {
  const eventDate = new Date(dateStr)
  const today = new Date()
  return (
    eventDate.getFullYear() === today.getFullYear() &&
    eventDate.getMonth() === today.getMonth() &&
    eventDate.getDate() === today.getDate()
  )
}

export function isThisWeek(dateStr: string): boolean {
  const eventDate = new Date(dateStr)
  const today = new Date()
  const weekFromNow = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000)
  return eventDate >= today && eventDate <= weekFromNow
}

export function groupEventsBySeries(events: Event[]): { standalone: Event[]; series: SeriesGroup[] } {
  const seriesMap = new Map<string, Event[]>()
  const standalone: Event[] = []

  for (const event of events) {
    if (event.series_id) {
      const existing = seriesMap.get(event.series_id) || []
      existing.push(event)
      seriesMap.set(event.series_id, existing)
    } else {
      standalone.push(event)
    }
  }

  const series: SeriesGroup[] = []
  for (const [series_id, groupEvents] of seriesMap.entries()) {
    if (groupEvents.length >= 2) {
      const firstEvent = groupEvents[0]
      if (firstEvent) {
        series.push({
          series_id,
          series_name: firstEvent.series_name || 'Event Series',
          events: groupEvents.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()),
        })
      }
    } else {
      standalone.push(...groupEvents)
    }
  }

  return { standalone, series }
}

export function isNewThisWeek(createdAt: string): boolean {
  const created = new Date(createdAt)
  const now = new Date()
  const threeDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
  return created >= threeDaysAgo
}

export function getCapacityUrgency(
  spotsRemaining: number | null,
  maxAttendees: number | null,
  t: (key: string, params?: Record<string, unknown>) => string,
  noUrgentLanguage = false
): { message: string | null; level: 'critical' | 'urgent' | 'warning' | 'normal' | 'full'; ariaLabel: string | null } {
  if (spotsRemaining === null || maxAttendees === null) {
    return { message: null, level: 'normal', ariaLabel: null }
  }
  // When noUrgentLanguage is enabled, always return plain factual messaging
  if (noUrgentLanguage && spotsRemaining > 0) {
    return {
      message: t('events.capacityNormal', { remaining: spotsRemaining, total: maxAttendees }),
      level: 'normal' as const,
      ariaLabel: t('events.capacityNormalAria', { remaining: spotsRemaining, total: maxAttendees }),
    }
  }
  if (spotsRemaining === 0) return { message: t('events.capacityFull'), level: 'full', ariaLabel: t('events.capacityFullAria') }
  if (spotsRemaining === 1) return { message: t('events.capacityLast'), level: 'critical', ariaLabel: t('events.capacityLastAria') }
  if (spotsRemaining < 5) return { message: t('events.capacityUrgent', { count: spotsRemaining }), level: 'urgent', ariaLabel: t('events.capacityUrgentAria', { count: spotsRemaining }) }
  return { message: t('events.capacityNormal', { remaining: spotsRemaining, total: maxAttendees }), level: 'normal', ariaLabel: t('events.capacityNormalAria', { remaining: spotsRemaining, total: maxAttendees }) }
}
