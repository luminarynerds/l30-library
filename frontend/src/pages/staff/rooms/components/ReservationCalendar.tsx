/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from "react"
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react"
import type { StaffReservation } from "../../../../api/staff-rooms-api"
import { getStatusColor, formatStatus } from "../constants"
import { useTranslation, getCurrentLocale } from '@/i18n'

interface ReservationCalendarProps {
  reservations?: StaffReservation[]
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 1).getDay()
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
]

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

export function ReservationCalendar({ reservations }: ReservationCalendarProps) {
  const { t } = useTranslation()
  const today = new Date()
  const [currentMonth, setCurrentMonth] = useState(today.getMonth())
  const [currentYear, setCurrentYear] = useState(today.getFullYear())
  const [selectedDate, setSelectedDate] = useState<string | null>(null)

  const daysInMonth = getDaysInMonth(currentYear, currentMonth)
  const firstDay = getFirstDayOfMonth(currentYear, currentMonth)

  const reservationsByDate = useMemo(() => {
    const map: Record<string, StaffReservation[]> = {}
    if (!reservations) return map
    for (const res of reservations) {
      const date = res.start_time.split("T")[0]
      if (date) {
        if (!map[date]) map[date] = []
        map[date].push(res)
      }
    }
    return map
  }, [reservations])

  const selectedDateReservations = selectedDate ? reservationsByDate[selectedDate] || [] : []

  const goToPrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11)
      setCurrentYear(currentYear - 1)
    } else {
      setCurrentMonth(currentMonth - 1)
    }
    setSelectedDate(null)
  }

  const goToNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0)
      setCurrentYear(currentYear + 1)
    } else {
      setCurrentMonth(currentMonth + 1)
    }
    setSelectedDate(null)
  }

  const goToToday = () => {
    setCurrentMonth(today.getMonth())
    setCurrentYear(today.getFullYear())
    const todayStr = today.toISOString().split("T")[0]!
    setSelectedDate(todayStr)
  }

  return (
    <div className="space-y-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
        {/* Calendar Header */}
        <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3">
            <CalendarDays className="w-5 h-5 text-lsc-rose" />
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              {MONTH_NAMES[currentMonth]} {currentYear}
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={goToToday}
              className="px-3 py-1 text-sm text-lsc-rose hover:bg-lsc-rose/10 rounded-lg"
            >
              Today
            </button>
            <button
              onClick={goToPrevMonth}
              aria-label={t('aria.reservationCalendar.previousMonth', 'Previous month')}
              className="p-1.5 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              onClick={goToNextMonth}
              aria-label={t('aria.reservationCalendar.nextMonth', 'Next month')}
              className="p-1.5 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Calendar Grid */}
        <div className="p-4">
          {/* Day Headers */}
          <div className="grid grid-cols-7 mb-2">
            {DAY_NAMES.map((day) => (
              <div
                key={day}
                className="text-center text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 py-2"
              >
                {day}
              </div>
            ))}
          </div>

          {/* Day Cells */}
          <div className="grid grid-cols-7 gap-1">
            {/* Empty cells for days before the 1st */}
            {Array.from({ length: firstDay }).map((_, i) => (
              <div key={`empty-${i}`} className="h-20" />
            ))}

            {/* Day cells */}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const day = i + 1
              const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`
              const dayReservations = reservationsByDate[dateStr] || []
              const isToday =
                day === today.getDate() &&
                currentMonth === today.getMonth() &&
                currentYear === today.getFullYear()
              const isSelected = selectedDate === dateStr

              return (
                <button
                  key={day}
                  onClick={() => setSelectedDate(dateStr)}
                  className={`h-20 rounded-lg p-1.5 text-left transition-colors border ${
                    isSelected
                      ? "border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10"
                      : isToday
                        ? "border-lsc-rose/30 bg-lsc-cream/50 dark:bg-earth-700/30"
                        : "border-transparent hover:bg-lsc-cream/50 dark:hover:bg-earth-700/30"
                  }`}
                >
                  <span
                    className={`text-sm font-medium ${
                      isToday
                        ? "text-lsc-rose"
                        : "text-lsc-dark dark:text-lsc-cream"
                    }`}
                  >
                    {day}
                  </span>
                  {dayReservations.length > 0 && (
                    <div className="mt-1 space-y-0.5">
                      {dayReservations.slice(0, 2).map((res) => (
                        <div
                          key={res.id}
                          className={`text-[10px] px-1 py-0.5 rounded truncate ${getStatusColor(res.status)}`}
                          title={res.room_name || `Room #${res.room_id}`}
                        >
                          {res.room_name || `Room #${res.room_id}`}
                        </div>
                      ))}
                      {dayReservations.length > 2 && (
                        <p className="text-[10px] text-lsc-dark/70 dark:text-lsc-cream/70 px-1">
                          +{dayReservations.length - 2} more
                        </p>
                      )}
                    </div>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Selected Date Details */}
      {selectedDate && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">
            {new Date(selectedDate + "T12:00:00").toLocaleDateString(getCurrentLocale(), {
              weekday: "long",
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </h4>

          {selectedDateReservations.length === 0 ? (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
              No reservations scheduled for this date.
            </p>
          ) : (
            <div className="space-y-2">
              {selectedDateReservations.map((res) => (
                <div
                  key={res.id}
                  className="flex items-center justify-between p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg"
                >
                  <div className="min-w-0">
                    <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">
                      {res.room_name || `Room #${res.room_id}`}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                      {new Date(res.start_time).toLocaleTimeString(getCurrentLocale(), {
                        hour: "numeric",
                        minute: "2-digit",
                      })}{" "}
                      -{" "}
                      {new Date(res.end_time).toLocaleTimeString(getCurrentLocale(), {
                        hour: "numeric",
                        minute: "2-digit",
                      })}
                      {" | "}
                      {res.patron_name || res.contact_name || "Unknown"}
                    </p>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 ${getStatusColor(res.status)}`}>
                    {formatStatus(res.status)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
