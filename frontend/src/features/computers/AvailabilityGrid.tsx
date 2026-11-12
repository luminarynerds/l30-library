/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'

interface RangeSlot {
  start_time: string
  end_time: string
  is_available: boolean
}

interface ComputerAvailabilityRow {
  computer_id: number
  name: string
  computer_number: string
  computer_type: string
  max_session_minutes: number
  slots: RangeSlot[]
}

interface AvailabilityGridProps {
  date: string
  onPick: (computerId: number, startTime: string, endTime: string) => void
}

/** All-computers free/busy grid for a date. Clicking a free cell books that slot. */
export function AvailabilityGrid({ date, onPick }: AvailabilityGridProps) {
  const [computers, setComputers] = useState<ComputerAvailabilityRow[]>([])
  const [loading, setLoading] = useState(false)

  const fetchRange = useCallback(async (d: string) => {
    setLoading(true)
    try {
      const data = await api.get(`${API_BASE}/computers/availability/range?date=${d}&days=1`)
      setComputers(data.computers || [])
    } catch {
      setComputers([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchRange(date) }, [date, fetchRange])

  if (loading) {
    return <div className="motion-safe:animate-pulse h-40 bg-earth-100 dark:bg-earth-800 rounded" />
  }

  if (computers.length === 0) {
    return (
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70" role="status">
        No computers available to book on this date.
      </p>
    )
  }

  // Every computer shares the library's hours for the day, so the first row's
  // slots define the column headers.
  const columns = computers[0]?.slots ?? []

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">Computer availability by hour. Choose an open slot to book.</caption>
        <thead>
          <tr>
            <th scope="col" className="text-left p-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
              Computer
            </th>
            {columns.map((s, i) => (
              <th
                key={i}
                scope="col"
                className="p-1 font-medium text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap"
              >
                {new Date(s.start_time).toLocaleTimeString([], { hour: 'numeric' })}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {computers.map(c => (
            <tr key={c.computer_id}>
              <th
                scope="row"
                className="text-left p-2 font-normal text-lsc-dark dark:text-lsc-cream whitespace-nowrap"
              >
                {c.name}{' '}
                <span className="text-lsc-dark/50 dark:text-lsc-cream/50">({c.computer_number})</span>
              </th>
              {c.slots.map((s, i) => (
                <td key={i} className="p-0.5">
                  <button
                    type="button"
                    disabled={!s.is_available}
                    onClick={() => onPick(c.computer_id, s.start_time, s.end_time)}
                    aria-label={`${s.is_available ? 'Book' : 'Booked'} ${c.name} at ${new Date(s.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}
                    className={`w-full h-8 rounded text-xs ${
                      s.is_available
                        ? 'bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 hover:bg-status-success-100 dark:hover:bg-status-success-900/30 cursor-pointer text-lsc-dark dark:text-lsc-cream'
                        : 'bg-earth-100 dark:bg-earth-800 text-earth-600 dark:text-earth-600 cursor-not-allowed'
                    }`}
                  >
                    {s.is_available ? '' : '×'}
                  </button>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
