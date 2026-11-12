/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/card'
import { useAvailability } from './useAvailability'

interface BookingCalendarProps {
  computerId?: number | undefined
  // Controlled date (YYYY-MM-DD). When provided, the calendar follows it and
  // hides its own date input (the page owns the date). Falls back to internal
  // state when omitted.
  date?: string | undefined
  onSlotSelect?: ((startTime: string, endTime: string) => void) | undefined
}

export function BookingCalendar({ computerId, date, onSlotSelect }: BookingCalendarProps) {
  const { slots, loading, fetchAvailability } = useAvailability()
  const [internalDate, setInternalDate] = useState(new Date().toISOString().split('T')[0]!)
  const selectedDate = date ?? internalDate

  useEffect(() => {
    fetchAvailability(selectedDate, computerId)
  }, [selectedDate, computerId, fetchAvailability])

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Book a Computer</CardTitle>
      </CardHeader>
      <CardContent>
        {date === undefined && (
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setInternalDate(e.target.value)}
            min={new Date().toISOString().split('T')[0]}
            className="w-full p-2 border border-lsc-border dark:border-earth-700 rounded mb-4 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          />
        )}
        {loading ? (
          <div className="motion-safe:animate-pulse space-y-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-10 bg-earth-100 dark:bg-earth-800 rounded" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {slots.map((slot, i) => (
              <button
                key={i}
                disabled={!slot.is_available}
                onClick={() => onSlotSelect?.(slot.start_time, slot.end_time)}
                className={`p-2 rounded text-sm text-center ${
                  slot.is_available
                    ? 'bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 hover:bg-status-success-100 dark:hover:bg-status-success-900/30 cursor-pointer text-lsc-dark dark:text-lsc-cream'
                    : 'bg-earth-100 dark:bg-earth-800 text-earth-600 dark:text-earth-600 cursor-not-allowed'
                }`}
              >
                {new Date(slot.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
