/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

interface ReservationCardProps {
  reservation: {
    id: number
    computer_id: number
    reserved_start_time: string
    reserved_end_time: string
    status: string
    created_at: string
  }
  onCancel?: (id: number) => void
  onCheckIn?: (id: number) => void
}

export function ReservationCard({ reservation, onCancel, onCheckIn }: ReservationCardProps) {
  const start = new Date(reservation.reserved_start_time)
  const end = new Date(reservation.reserved_end_time)
  const canCancel = !['completed', 'cancelled', 'no_show'].includes(reservation.status)
  const canCheckIn = reservation.status === 'confirmed'

  return (
    <div className="p-4 border border-lsc-border dark:border-earth-700 rounded-lg">
      <div className="flex justify-between items-start">
        <div>
          <div className="font-medium text-lsc-dark dark:text-lsc-cream">Computer #{reservation.computer_id}</div>
          <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {start.toLocaleDateString()} {start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
          <span className={`inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium ${
            reservation.status === 'confirmed' ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300' :
            reservation.status === 'pending' ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300' :
            'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
          }`}>
            {reservation.status}
          </span>
        </div>
        <div className="flex gap-2">
          {canCheckIn && (
            <button onClick={() => onCheckIn?.(reservation.id)} className="px-3 py-1 bg-status-success-600 text-white text-sm rounded">
              Check In
            </button>
          )}
          {canCancel && (
            <button onClick={() => onCancel?.(reservation.id)} className="px-3 py-1 border border-lsc-border dark:border-earth-700 text-status-danger-600 dark:text-status-danger-400 text-sm rounded">
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
