/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'
import type { Computer } from '@/types/computer'
import { ComputerReservationCard } from './ComputerReservationCard'
import { useComputerSessions } from './useComputerSessions'

interface StationListProps {
  onReserve: (computerId: number, startTime: Date, durationMinutes: number) => void | Promise<void>
  onStartSession: (computerId: number, durationMinutes: number) => void | Promise<void>
}

export function StationList({ onReserve, onStartSession }: StationListProps) {
  const { stations, loading, error, fetchStations } = useComputerSessions()

  useEffect(() => { fetchStations() }, [fetchStations])

  if (loading) return <div className="motion-safe:animate-pulse h-48 bg-earth-100 dark:bg-earth-800 rounded-lg" />

  if (error) {
    return (
      <div
        role="alert"
        className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg text-sm text-status-danger-800 dark:text-status-danger-300"
      >
        {error}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {stations.map((station) => (
        <ComputerReservationCard
          key={station.id}
          // ComputerStation from useComputerSessions is a structural subset of
          // Computer — fields ComputerReservationCard reads but ComputerStation
          // lacks (has_print_release, has_screen_reader, has_magnifier,
          // has_keyboard_options, is_extendable) gate optional UI via truthy
          // checks, so undefined is safe at runtime. Cast bridges the two.
          computer={station as unknown as Computer}
          isAvailable={station.status === 'available'}
          onReserve={onReserve}
          onStartSession={onStartSession}
        />
      ))}
    </div>
  )
}
