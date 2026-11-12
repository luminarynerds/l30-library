/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useMemo } from 'react'
import type { Event } from '@/api/api'
import { clsx } from '@/utils/helpers'
import { t } from '@/i18n'
import EventCard from './EventCard'
import { DAYS_OF_WEEK, getDaysInMonth } from './utils'

interface MonthViewProps {
  currentDate: Date
  events: Event[]
  onEventClick: (event: Event) => void
  selectedDate: Date | null
  onDateSelect: (date: Date) => void
  locale: string
}

const MonthView = React.memo(function MonthView({
  currentDate,
  events,
  onEventClick,
  selectedDate,
  onDateSelect,
  locale,
}: MonthViewProps) {
  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()
  const firstDay = new Date(year, month, 1)
  const daysInMonth = getDaysInMonth(year, month)
  const startingDayOfWeek = firstDay.getDay()
  const today = new Date()
  const isCurrentMonth = today.getFullYear() === year && today.getMonth() === month

  const eventsByDay = useMemo(
    () =>
      events.reduce(
        (acc, event) => {
          const eventDate = new Date(event.start_time)
          if (eventDate.getFullYear() === year && eventDate.getMonth() === month) {
            const day = eventDate.getDate()
            if (!acc[day]) acc[day] = []
            acc[day]!.push(event)
          }
          return acc
        },
        {} as Record<number, Event[]>
      ),
    [events, year, month]
  )

  const calendarDays: React.ReactElement[] = []

  for (let i = 0; i < startingDayOfWeek; i++) {
    calendarDays.push(<div key={`empty-${i}`} className="p-1.5 sm:p-2 min-h-[80px] sm:min-h-[100px]" />)
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const isToday = isCurrentMonth && today.getDate() === day
    const dayEvents = eventsByDay[day] || []
    const hasEvents = dayEvents.length > 0
    const isSelected = selectedDate && selectedDate.getDate() === day &&
      selectedDate.getMonth() === month && selectedDate.getFullYear() === year

    const cellClass = clsx(
      'p-1.5 sm:p-2 min-h-[80px] sm:min-h-[100px] border border-lsc-border dark:border-earth-700 transition-colors cursor-pointer',
      isSelected
        ? 'bg-forest-500/10 dark:bg-forest-500/20 ring-2 ring-forest-500'
        : isToday
          ? 'bg-status-info-50 dark:bg-status-info-900/20 ring-2 ring-status-info-500'
          : hasEvents
            ? 'bg-status-warning-50/80 dark:bg-status-warning-900/10 hover:bg-status-warning-100/80 dark:hover:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800/30'
            : 'bg-lsc-white dark:bg-earth-800 hover:bg-lsc-cream dark:hover:bg-lsc-brown/10'
    )

    const dayClass = clsx(
      'text-sm font-semibold mb-1',
      isToday
        ? 'text-status-info-600 dark:text-status-info-400'
        : 'text-lsc-dark dark:text-lsc-cream/80'
    )

    calendarDays.push(
      <div
        key={day}
        className={cellClass}
        onClick={() => onDateSelect(new Date(year, month, day))}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onDateSelect(new Date(year, month, day))
          }
        }}
        role="gridcell"
        aria-label={`${new Date(year, month, day).toLocaleDateString(locale, { weekday: 'long', month: 'long', day: 'numeric' })}${hasEvents ? `, ${dayEvents.length} event${dayEvents.length > 1 ? 's' : ''}` : ''}`}
        tabIndex={isToday || isSelected ? 0 : -1}
      >
        <div className={dayClass}>{day}</div>
        <div className="space-y-1">
          {dayEvents.slice(0, 3).map((event) => (
            <EventCard
              key={event.id}
              event={event}
              onClick={() => onEventClick(event)}
              compact
              locale={locale}
            />
          ))}
          {dayEvents.length > 3 && (
            <div className="text-xs text-forest-800 dark:text-forest-500 font-medium">
              +{dayEvents.length - 3} more
            </div>
          )}
        </div>
      </div>
    )
  }

  const mobileDays = useMemo(() => {
    const days: { day: number; date: Date; events: Event[] }[] = []
    for (let d = 1; d <= daysInMonth; d++) {
      const dayEvents = eventsByDay[d]
      if (dayEvents && dayEvents.length > 0) {
        days.push({ day: d, date: new Date(year, month, d), events: dayEvents })
      }
    }
    return days
  }, [eventsByDay, daysInMonth, year, month])

  return (
    <>
      {/* Mobile: list view grouped by date */}
      <div className="block sm:hidden">
        {mobileDays.length === 0 ? (
          <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            No events this month
          </div>
        ) : (
          <div className="space-y-4">
            {mobileDays.map(({ day, date, events: dayEvents }) => {
              const isToday = isCurrentMonth && today.getDate() === day
              const isSelected = selectedDate && selectedDate.getDate() === day &&
                selectedDate.getMonth() === month && selectedDate.getFullYear() === year

              return (
                <div key={day}>
                  <button
                    onClick={() => onDateSelect(new Date(year, month, day))}
                    className={clsx(
                      'w-full text-left px-3 py-2 rounded-lg font-semibold text-sm flex items-center gap-2 transition-colors',
                      isSelected
                        ? 'bg-forest-700/10 dark:bg-forest-500/20 text-forest-800 dark:text-forest-500'
                        : isToday
                          ? 'bg-status-info-50 dark:bg-status-info-900/20 text-status-info-600 dark:text-status-info-400'
                          : 'text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/10'
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
                      {day}
                    </span>
                    <span>
                      {date.toLocaleDateString(locale, { weekday: 'long', month: 'short', day: 'numeric' })}
                    </span>
                    <span className="ml-auto text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {dayEvents.length} event{dayEvents.length !== 1 ? 's' : ''}
                    </span>
                  </button>
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
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Desktop: full calendar grid */}
      <div className="hidden sm:block">
        <div className="grid grid-cols-7 gap-0 mb-2" role="row">
          {DAYS_OF_WEEK.map((day) => (
            <div
              key={day}
              className="p-2 text-center text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70"
              role="columnheader"
            >
              {day}
            </div>
          ))}
        </div>

        <div
          className="grid grid-cols-7 gap-0 border-t border-l border-lsc-border dark:border-earth-700"
          role="grid"
          aria-label={t('aria.eventCalendarView.monthCalendarGrid')}
        >
          {calendarDays}
        </div>
      </div>
    </>
  )
})

export default MonthView
