/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useMemo } from 'react'
import type { Event } from '@/api/api'
import { clsx } from '@/utils/helpers'
import { t } from '@/i18n'
import EventCard from './EventCard'
import { formatDateKey, getEndOfWeek, getStartOfWeek, isSameDay } from './utils'

interface WeekViewProps {
  currentDate: Date
  events: Event[]
  onEventClick: (event: Event) => void
  selectedDate: Date | null
  locale: string
}

const WeekView = React.memo(function WeekView({
  currentDate,
  events,
  onEventClick,
  selectedDate,
  locale,
}: WeekViewProps) {
  const weekStart = getStartOfWeek(currentDate)
  const today = new Date()

  const weekDays = useMemo(() => {
    const days: Date[] = []
    for (let i = 0; i < 7; i++) {
      const d = new Date(weekStart)
      d.setDate(weekStart.getDate() + i)
      days.push(d)
    }
    return days
  }, [weekStart])

  const eventsByDay = useMemo(() => {
    const map: Record<string, Event[]> = {}
    const weekEnd = getEndOfWeek(currentDate)

    events.forEach((event) => {
      const eventDate = new Date(event.start_time)
      if (eventDate >= weekStart && eventDate <= weekEnd) {
        const key = formatDateKey(eventDate)
        if (!map[key]) map[key] = []
        map[key]!.push(event)
      }
    })

    Object.keys(map).forEach((key) => {
      const dayEvents = map[key]
      if (dayEvents) {
        dayEvents.sort(
          (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
        )
      }
    })

    return map
  }, [events, weekStart, currentDate])

  return (
    <>
      {/* Mobile: vertical day-by-day list */}
      <div className="block sm:hidden space-y-4">
        {weekDays.map((day) => {
          const key = formatDateKey(day)
          const dayEvents = eventsByDay[key] || []
          const isToday = isSameDay(day, today)
          const isSelected = selectedDate && isSameDay(day, selectedDate)

          return (
            <div key={key}>
              <div
                className={clsx(
                  'flex items-center gap-2 px-3 py-2 rounded-lg font-semibold text-sm',
                  isSelected
                    ? 'bg-forest-700/10 dark:bg-forest-500/20 text-forest-800 dark:text-forest-500'
                    : isToday
                      ? 'bg-status-info-50 dark:bg-status-info-900/20 text-status-info-600 dark:text-status-info-400'
                      : 'text-lsc-dark dark:text-lsc-cream'
                )}
              >
                <span className={clsx(
                  'inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold',
                  isSelected
                    ? 'bg-forest-800 text-white'
                    : isToday
                      ? 'ring-2 ring-status-info-500'
                      : ''
                )}>
                  {day.getDate()}
                </span>
                <span>{day.toLocaleDateString(locale, { weekday: 'long', month: 'short', day: 'numeric' })}</span>
              </div>
              {dayEvents.length === 0 ? (
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-3">
                  No events
                </div>
              ) : (
                <div className="mt-1 space-y-1 pl-2">
                  {dayEvents.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      onClick={() => onEventClick(event)}
                      locale={locale}
                    />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Desktop: full 7-column grid */}
      <div className="hidden sm:block">
        <div className="grid grid-cols-7 gap-2 mb-3" role="row">
          {weekDays.map((day) => {
            const isToday = isSameDay(day, today)
            const isSelected = selectedDate && isSameDay(day, selectedDate)

            return (
              <div
                key={day.toISOString()}
                className={clsx(
                  'text-center p-2 rounded-lg transition-colors',
                  isSelected
                    ? 'bg-forest-800 text-white'
                    : isToday
                      ? 'bg-status-info-50 dark:bg-status-info-900/20 ring-1 ring-status-info-500'
                      : ''
                )}
                role="columnheader"
              >
                <div
                  className={clsx(
                    'text-xs font-medium',
                    isSelected
                      ? 'text-white/80'
                      : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                  )}
                >
                  {day.toLocaleDateString(locale, { weekday: 'short' })}
                </div>
                <div
                  className={clsx(
                    'text-lg font-bold',
                    isSelected
                      ? 'text-white'
                      : isToday
                        ? 'text-status-info-600 dark:text-status-info-400'
                        : 'text-lsc-dark dark:text-lsc-cream'
                  )}
                >
                  {day.getDate()}
                </div>
              </div>
            )
          })}
        </div>

        <div
          className="grid grid-cols-7 gap-2"
          role="grid"
          aria-label={t('aria.eventCalendarView.weekCalendarGrid')}
        >
          {weekDays.map((day) => {
            const key = formatDateKey(day)
            const dayEvents = eventsByDay[key] || []

            return (
              <div
                key={key}
                className="min-h-[200px] bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-2 space-y-2"
                role="gridcell"
                aria-label={`${day.toLocaleDateString(locale, { weekday: 'long', month: 'long', day: 'numeric' })}, ${dayEvents.length} events`}
              >
                {dayEvents.length === 0 ? (
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-4">
                    No events
                  </div>
                ) : (
                  dayEvents.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      onClick={() => onEventClick(event)}
                      locale={locale}
                    />
                  ))
                )}
              </div>
            )
          })}
        </div>
      </div>
    </>
  )
})

export default WeekView
