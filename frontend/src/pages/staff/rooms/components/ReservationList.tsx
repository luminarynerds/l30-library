/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Calendar, Eye, AlertCircle } from "lucide-react"
import type { StaffReservation } from "../../../../api/staff-rooms-api"
import { getStatusColor, formatStatus, formatDateTime } from "../constants"
import { useTranslation } from '@/i18n'

const RESERVATION_STATUSES = [
  { value: "", label: "All Statuses" },
  { value: "pending", label: "Pending" },
  { value: "confirmed", label: "Confirmed" },
  { value: "checked_in", label: "Checked In" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "no_show", label: "No Show" },
  { value: "rejected", label: "Rejected" },
]

interface ReservationListProps {
  reservations: StaffReservation[] | undefined
  pendingReservations: StaffReservation[] | undefined
  isLoading: boolean
  reservationStatus: string
  reservationDateFrom: string
  reservationDateTo: string
  locale: string
  onStatusFilterChange: (value: string) => void
  onDateFromChange: (value: string) => void
  onDateToChange: (value: string) => void
  onViewReservation: (id: number) => void
}

export function ReservationList({
  reservations,
  pendingReservations,
  isLoading,
  reservationStatus,
  reservationDateFrom,
  reservationDateTo,
  locale,
  onStatusFilterChange,
  onDateFromChange,
  onDateToChange,
  onViewReservation,
}: ReservationListProps) {
  const { t } = useTranslation()
  return (
    <div className="space-y-4">
      {/* Pending Reservations Alert */}
      {pendingReservations && pendingReservations.length > 0 && (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800/50 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400" />
            <h3 className="font-serif font-semibold text-status-warning-800 dark:text-status-warning-300">
              {pendingReservations.length} Pending Approval{pendingReservations.length !== 1 ? "s" : ""}
            </h3>
          </div>
          <div className="space-y-2">
            {pendingReservations.slice(0, 5).map((res) => (
              <div
                key={res.id}
                className="flex items-center justify-between bg-lsc-white dark:bg-earth-800 rounded-lg p-3 border border-status-warning-100 dark:border-status-warning-900/30"
              >
                <div className="min-w-0">
                  <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate">
                    {res.room_name || `Room #${res.room_id}`} - {res.patron_name || res.contact_name || "Unknown"}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                    {formatDateTime(res.start_time, locale)}
                    {res.purpose && ` - ${res.purpose}`}
                  </p>
                </div>
                <button
                  onClick={() => onViewReservation(res.id)}
                  className="flex-shrink-0 flex items-center gap-1 px-3 py-1 text-sm text-lsc-rose hover:bg-lsc-rose/10 rounded-lg"
                >
                  <Eye className="w-3 h-3" /> Review
                </button>
              </div>
            ))}
            {pendingReservations.length > 5 && (
              <p className="text-sm text-status-warning-700 dark:text-status-warning-400 text-center">
                +{pendingReservations.length - 5} more pending
              </p>
            )}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={reservationStatus}
          onChange={(e) => onStatusFilterChange(e.target.value)}
          aria-label={t('aria.reservationList.filterByStatus', 'Filter by status')}
          className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
        >
          {RESERVATION_STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <label htmlFor="reservation-date-from" className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">From</label>
          <input
            id="reservation-date-from"
            type="date"
            value={reservationDateFrom}
            onChange={(e) => onDateFromChange(e.target.value)}
            className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
          />
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="reservation-date-to" className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">To</label>
          <input
            id="reservation-date-to"
            type="date"
            value={reservationDateTo}
            onChange={(e) => onDateToChange(e.target.value)}
            className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
          />
        </div>

        {(reservationStatus || reservationDateFrom || reservationDateTo) && (
          <button
            onClick={() => {
              onStatusFilterChange("")
              onDateFromChange("")
              onDateToChange("")
            }}
            className="text-sm text-lsc-rose hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Reservations Table */}
      <div>
      {isLoading ? (
        <div role="status" aria-live="polite" className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
          <span className="sr-only">{t('reservationList.loadingReservations', 'Loading reservations…')}</span>
        </div>
      ) : !reservations || reservations.length === 0 ? (
        <div role="status" aria-live="polite" className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
          <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" aria-hidden="true" />
          <p>No reservations found</p>
          {(reservationStatus || reservationDateFrom || reservationDateTo) && (
            <p className="text-sm mt-1">{t('reservationList.tryAdjustingYourFilters')}</p>
          )}
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-lsc-dark/70 dark:text-lsc-cream/70 border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-700/50">
                  <th className="py-3 px-4 font-medium">Room</th>
                  <th className="py-3 px-4 font-medium">Patron</th>
                  <th className="py-3 px-4 font-medium">Date/Time</th>
                  <th className="py-3 px-4 font-medium">Purpose</th>
                  <th className="py-3 px-4 font-medium">Status</th>
                  <th className="py-3 px-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {reservations.map((reservation) => (
                  <tr
                    key={reservation.id}
                    className="hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors"
                  >
                    <td className="py-3 px-4 text-lsc-dark dark:text-lsc-cream">
                      {reservation.room_name || `Room #${reservation.room_id}`}
                    </td>
                    <td className="py-3 px-4 text-lsc-dark/80 dark:text-lsc-cream/80">
                      <div>
                        {reservation.patron_name || reservation.contact_name || "Unknown"}
                        {reservation.attendee_count && (
                          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 ml-1">
                            ({reservation.attendee_count} attendees)
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {formatDateTime(reservation.start_time, locale)}
                    </td>
                    <td className="py-3 px-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/60 max-w-[12.5rem] truncate" title={reservation.purpose || "-"}>
                      {reservation.purpose || "-"}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(reservation.status)}`}
                      >
                        {formatStatus(reservation.status)}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => onViewReservation(reservation.id)}
                        className="flex items-center gap-1 text-sm text-lsc-rose hover:underline"
                      >
                        <Eye className="w-3 h-3" /> View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div role="status" aria-live="polite" className="px-4 py-3 border-t border-lsc-border dark:border-earth-700 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
            Showing {reservations.length} reservation{reservations.length !== 1 ? "s" : ""}
          </div>
        </div>
      )}
      </div>
    </div>
  )
}
