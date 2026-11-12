/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import React, { useCallback, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, Download } from 'lucide-react'
import type { Event } from '@/api/api'
import { clsx } from '@/utils/helpers'
import { useLanguage } from '@/i18n/I18nContext'
import { getLocale } from '@/i18n/localization'
import { t } from '@/i18n'
import CalendarExportMenu from './CalendarExportMenu'
import MiniCalendar from './MiniCalendar'
import MonthView from './MonthView'
import WeekView from './WeekView'
import { type CalendarViewMode, formatDateKey, getEndOfWeek, getStartOfWeek } from './utils'

export type { CalendarViewMode }

interface EventCalendarViewProps {
  events: Event[]
  onEventClick: (event: Event) => void
  onRegister: (event: Event) => void
  viewMode?: CalendarViewMode
  showMiniCalendar?: boolean
  onDateSelect?: (date: Date) => void
  selectedDate?: Date | null
}

const EventCalendarView = React.memo(function EventCalendarView({
  events,
  onEventClick,
  onRegister: _onRegister,
  viewMode = 'month',
  showMiniCalendar = false,
  onDateSelect,
  selectedDate: externalSelectedDate,
}: EventCalendarViewProps) {
  const { language } = useLanguage()
  const locale = getLocale(language)
  const [currentDate, setCurrentDate] = useState(new Date())
  const [internalSelectedDate, setInternalSelectedDate] = useState<Date | null>(null)
  const [showExportMenu, setShowExportMenu] = useState(false)

  const selectedDate = externalSelectedDate ?? internalSelectedDate

  const handleDateSelect = useCallback(
    (date: Date) => {
      setInternalSelectedDate(date)
      if (onDateSelect) {
        onDateSelect(date)
      }
      setCurrentDate(date)
    },
    [onDateSelect]
  )

  const eventDates = useMemo(() => {
    const dates = new Set<string>()
    events.forEach((event) => {
      const date = new Date(event.start_time)
      dates.add(formatDateKey(date))
    })
    return dates
  }, [events])

  const goToPrevious = () => {
    if (viewMode === 'month') {
      setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1))
    } else {
      const newDate = new Date(currentDate)
      newDate.setDate(currentDate.getDate() - 7)
      setCurrentDate(newDate)
    }
  }

  const goToNext = () => {
    if (viewMode === 'month') {
      setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1))
    } else {
      const newDate = new Date(currentDate)
      newDate.setDate(currentDate.getDate() + 7)
      setCurrentDate(newDate)
    }
  }

  const goToToday = () => {
    const today = new Date()
    setCurrentDate(today)
    handleDateSelect(today)
  }

  const getHeaderTitle = () => {
    if (viewMode === 'month') {
      return currentDate.toLocaleDateString(locale, { month: 'long', year: 'numeric' })
    }
    const weekStart = getStartOfWeek(currentDate)
    const weekEnd = getEndOfWeek(currentDate)
    const startMonth = weekStart.toLocaleDateString(locale, { month: 'short' })
    const endMonth = weekEnd.toLocaleDateString(locale, { month: 'short' })
    const year = weekEnd.getFullYear()

    if (startMonth === endMonth) {
      return `${startMonth} ${weekStart.getDate()}-${weekEnd.getDate()}, ${year}`
    }
    return `${startMonth} ${weekStart.getDate()} - ${endMonth} ${weekEnd.getDate()}, ${year}`
  }

  return (
    <div className={clsx('flex gap-4', showMiniCalendar ? 'flex-col lg:flex-row' : '')}>
      {showMiniCalendar && (
        <div className="w-full lg:w-auto lg:flex-shrink-0">
          <MiniCalendar
            currentDate={currentDate}
            selectedDate={selectedDate}
            onDateSelect={handleDateSelect}
            onMonthChange={setCurrentDate}
            eventDates={eventDates}
            locale={locale}
          />
        </div>
      )}

      <div className="flex-1 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 sm:p-6">
        <div className="flex items-center justify-between mb-4 sm:mb-6 flex-wrap gap-2">
          <h2 className="text-xl sm:text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {getHeaderTitle()}
          </h2>
          <div className="flex items-center gap-1 sm:gap-2">
            <div className="relative">
              <button
                onClick={() => setShowExportMenu(!showExportMenu)}
                className="p-1.5 sm:p-2 rounded-lg text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                aria-label={t('aria.eventCalendarView.exportCalendar')}
                aria-expanded={showExportMenu}
                aria-haspopup="menu"
              >
                <Download className="w-4 h-4 sm:w-5 sm:h-5" />
              </button>
              {showExportMenu && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setShowExportMenu(false)}
                    aria-hidden="true"
                  />
                  <CalendarExportMenu events={events} onClose={() => setShowExportMenu(false)} />
                </>
              )}
            </div>

            <button
              onClick={goToToday}
              className="px-2 sm:px-3 py-1.5 text-xs sm:text-sm font-medium text-status-info-600 dark:text-status-info-400 hover:bg-status-info-50 dark:hover:bg-status-info-900/20 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-status-info-500"
            >
              Today
            </button>
            <button
              onClick={goToPrevious}
              aria-label={viewMode === 'month' ? 'Previous month' : 'Previous week'}
              className="p-1.5 sm:p-2 rounded-lg text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              <ChevronLeft className="w-4 h-4 sm:w-5 sm:h-5" />
            </button>
            <button
              onClick={goToNext}
              aria-label={viewMode === 'month' ? 'Next month' : 'Next week'}
              className="p-1.5 sm:p-2 rounded-lg text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              <ChevronRight className="w-4 h-4 sm:w-5 sm:h-5" />
            </button>
          </div>
        </div>

        {viewMode === 'month' ? (
          <MonthView
            currentDate={currentDate}
            events={events}
            onEventClick={onEventClick}
            selectedDate={selectedDate}
            onDateSelect={handleDateSelect}
            locale={locale}
          />
        ) : (
          <WeekView
            currentDate={currentDate}
            events={events}
            onEventClick={onEventClick}
            selectedDate={selectedDate}
            locale={locale}
          />
        )}

        <div className="mt-4 flex flex-wrap items-center gap-3 sm:gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-status-info-50 dark:bg-status-info-900/20 ring-2 ring-status-info-500 rounded" />
            <span>Today</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-status-warning-50/80 dark:bg-status-warning-900/10 border border-status-warning-200 dark:border-status-warning-800/30 rounded" />
            <span>Has events</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-forest-500/10 dark:bg-forest-500/20 ring-2 ring-forest-500 rounded" />
            <span>Selected</span>
          </div>
        </div>
      </div>
    </div>
  )
})

export default EventCalendarView

export {
  downloadICalEvent,
  downloadICalFeed,
  generateGoogleCalendarUrl,
} from '@/utils/calendarExport'
