/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { RoomUtilizationByRoom } from "./types"

interface RoomPerformanceTableProps {
  rooms: RoomUtilizationByRoom[]
}

export function RoomPerformanceTable({ rooms }: RoomPerformanceTableProps): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700">
      <div className="p-6 border-b border-lsc-border dark:border-earth-700">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Detailed Room Performance
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-lsc-cream dark:bg-lsc-brown">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark dark:text-lsc-cream">
                Room Name
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark dark:text-lsc-cream">
                Type
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark dark:text-lsc-cream">
                Total Reservations
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark dark:text-lsc-cream">
                Confirmed
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark dark:text-lsc-cream">
                Hours Booked
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark dark:text-lsc-cream">
                Utilization
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
            {rooms.map((room) => (
              <tr key={room.room_id} className="hover:bg-lsc-cream dark:hover:bg-lsc-brown/50">
                <td className="px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {room.room_name}
                </td>
                <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {room.room_type}
                </td>
                <td className="px-4 py-3 text-sm text-right text-lsc-dark dark:text-lsc-cream">
                  {room.total_reservations}
                </td>
                <td className="px-4 py-3 text-sm text-right text-lsc-dark dark:text-lsc-cream">
                  {room.confirmed_reservations}
                </td>
                <td className="px-4 py-3 text-sm text-right text-lsc-dark dark:text-lsc-cream">
                  {room.hours_booked.toFixed(1)}
                </td>
                <td className="px-4 py-3 text-sm text-right">
                  <span className={`font-semibold ${utilizationColor(room.utilization_rate)}`}>
                    {room.utilization_rate.toFixed(1)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function utilizationColor(rate: number): string {
  if (rate >= 75) return "text-status-success-600 dark:text-status-success-400"
  if (rate >= 50) return "text-lsc-rose"
  return "text-status-danger-600 dark:text-status-danger-400"
}
