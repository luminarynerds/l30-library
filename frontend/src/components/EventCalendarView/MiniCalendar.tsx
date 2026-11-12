/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation } from '@/i18n'
import {
  DAYS_OF_WEEK_SHORT,
  formatDateKey,
  getDaysInMonth,
  isSameDay,
} from './utils'

interface MiniCalendarProps {
  currentDate: Date
  selectedDate: Date | null
  onDateSelect: (date: Date) => void
  onMonthChange: (date: Date) => void
  eventDates: Set<string>
  locale: string
}

const MiniCalendar = React.memo(function MiniCalendar({
  currentDate,
  selectedDate,
  onDateSelect,
  onMonthChange,
  eventDates,
  locale,
}: MiniCalendarProps) {
  const { t } = useTranslation()
  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()
  const firstDay = new Date(year, month, 1)
  const daysInMonth = getDaysInMonth(year, month)
  const startingDay = firstDay.getDay()
  const today = new Date()

  const handlePrevMonth = () => onMonthChange(new Date(year, month - 1, 1))
  const handleNextMonth = () => onMonthChange(new Date(year, month + 1, 1))

  const handleKeyDown = (e: React.KeyboardEvent, day: number) => {
    const currentDay = selectedDate?.getDate() || today.getDate()
    let newDay = currentDay

    switch (e.key) {
      case 'ArrowLeft':
        newDay = Math.max(1, currentDay - 1)
        e.preventDefault()
        break
      case 'ArrowRight':
        newDay = Math.min(daysInMonth, currentDay + 1)
        e.preventDefault()
        break
      case 'ArrowUp':
        newDay = Math.max(1, currentDay - 7)
        e.preventDefault()
        break
      case 'ArrowDown':
        newDay = Math.min(daysInMonth, currentDay + 7)
        e.preventDefault()
        break
      case 'Enter':
      case ' ':
        onDateSelect(new Date(year, month, day))
        e.preventDefault()
        return
      default:
        return
    }

    onDateSelect(new Date(year, month, newDay))
  }

  const days: React.ReactElement[] = []

  for (let i = 0; i < startingDay; i++) {
    days.push(<div key={`empty-${i}`} className="w-7 h-7" aria-hidden="true" />)
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const date = new Date(year, month, day)
    const dateKey = formatDateKey(date)
    const isToday = isSameDay(date, today)
    const isSelected = selectedDate && isSameDay(date, selectedDate)
    const hasEvents = eventDates.has(dateKey)

    days.push(
      <button
        key={day}
        onClick={() => onDateSelect(date)}
        onKeyDown={(e) => handleKeyDown(e, day)}
        className={clsx(
          'w-7 h-7 text-xs rounded-full flex items-center justify-center relative transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1',
          isSelected
            ? 'bg-forest-800 text-white font-semibold'
            : isToday
              ? 'bg-status-info-50 dark:bg-status-info-900/30 ring-1 ring-status-info-500 text-status-info-600 dark:text-status-info-400 font-semibold'
              : 'hover:bg-lsc-cream dark:hover:bg-lsc-brown text-lsc-dark dark:text-lsc-cream'
        )}
        aria-label={`${date.toLocaleDateString(locale, { weekday: 'long', month: 'long', day: 'numeric' })}${hasEvents ? ', has events' : ''}`}
        aria-pressed={isSelected || undefined}
        tabIndex={isSelected || (day === 1 && !selectedDate) ? 0 : -1}
      >
        {day}
        {hasEvents && !isSelected && (
          <span
            className="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-forest-500 dark:bg-forest-500"
            aria-hidden="true"
          />
        )}
      </button>
    )
  }

  const monthName = currentDate.toLocaleDateString(locale, { month: 'short', year: 'numeric' })

  return (
    <div
      className="bg-lsc-white dark:bg-earth-800 rounded-xl p-3 shadow-sm border border-lsc-border dark:border-earth-700"
      role="application"
      aria-label={t('components.eventCalendarView.miniCalendarForDateNavigation')}
    >
      <div className="flex items-center justify-between mb-2">
        <button
          onClick={handlePrevMonth}
          className="p-1 rounded hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          aria-label={t('aria.eventCalendarView.previousMonth')}
        >
          <ChevronLeft className="w-4 h-4 text-lsc-dark dark:text-lsc-cream" />
        </button>
        <span className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
          {monthName}
        </span>
        <button
          onClick={handleNextMonth}
          className="p-1 rounded hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          aria-label={t('aria.eventCalendarView.nextMonth')}
        >
          <ChevronRight className="w-4 h-4 text-lsc-dark dark:text-lsc-cream" />
        </button>
      </div>

      <div className="grid grid-cols-7 gap-0.5 mb-1">
        {DAYS_OF_WEEK_SHORT.map((day, i) => (
          <div
            key={day + i}
            className="w-7 h-6 flex items-center justify-center text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70"
            aria-hidden="true"
          >
            {day}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-0.5" role="grid" aria-label={t('aria.eventCalendarView.calendarDays')}>
        {days}
      </div>

      <button
        onClick={() => {
          const now = new Date()
          onMonthChange(now)
          onDateSelect(now)
        }}
        className="mt-2 w-full text-xs text-center text-status-info-600 dark:text-status-info-400 hover:underline focus:outline-none focus:ring-2 focus:ring-status-info-500 rounded py-1"
      >
        Today
      </button>
    </div>
  )
})

export default MiniCalendar
