/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { Loader2, DoorOpen, Clock, Users, FileText, Check, X, LogIn, XCircle } from "lucide-react"
import type { StaffReservationDetail } from "../../../../api/staff-rooms-api"
import { getStatusColor, formatStatus, formatDateTime, REJECTION_REASON_CODES, type RejectionReasonCode } from "../constants"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { t } from '@/i18n'

interface ReservationDetailModalProps {
  reservation: StaffReservationDetail | null
  isLoading: boolean
  locale: string
  onClose: () => void
  onApprove: () => void
  onReject: (reasonCode: RejectionReasonCode, reasonText: string) => void
  onCancel: () => void
  onCheckIn: () => void
  isApproving: boolean
  isCancelling: boolean
  isCheckingIn: boolean
}

export function ReservationDetailModal({
  reservation,
  isLoading,
  locale,
  onClose,
  onApprove,
  onReject,
  onCancel,
  onCheckIn,
  isApproving,
  isCancelling,
  isCheckingIn,
}: ReservationDetailModalProps) {
  const [confirmRejectOpen, setConfirmRejectOpen] = useState(false)
  const [rejectReasonCode, setRejectReasonCode] = useState<RejectionReasonCode>("other")

  if (isLoading) {
    return (
      <ModalBackdrop title="Dialog">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      </ModalBackdrop>
    )
  }

  if (!reservation) return null

  const patronLabel = reservation.patron_name || reservation.contact_name || "Unknown"

  return (
    <>
    <ModalBackdrop onClose={onClose} title="Reservation Details" role="alertdialog">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-lsc-border dark:border-earth-700 flex justify-between items-start">
          <div>
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              Reservation Details
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              #{reservation.id}
            </p>
          </div>
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(reservation.status)}`}>
            {formatStatus(reservation.status)}
          </span>
        </div>

        <div className="p-6 space-y-4">
          {/* Room Info */}
          <div className="flex items-start gap-3">
            <DoorOpen className="w-5 h-5 text-lsc-rose mt-0.5" />
            <div>
              <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                {reservation.room_name || `Room #{reservation.room_id}`}
              </p>
            </div>
          </div>

          {/* Time */}
          <div className="flex items-start gap-3">
            <Clock className="w-5 h-5 text-lsc-rose mt-0.5" />
            <div>
              <p className="text-lsc-dark dark:text-lsc-cream">
                {formatDateTime(reservation.start_time, locale)}
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                to {formatDateTime(reservation.end_time, locale)}
              </p>
            </div>
          </div>

          {/* Contact */}
          <div className="flex items-start gap-3">
            <Users className="w-5 h-5 text-lsc-rose mt-0.5" />
            <div>
              <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                {reservation.patron_name || reservation.contact_name || "Unknown"}
              </p>
              {reservation.contact_email && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {reservation.contact_email}
                </p>
              )}
              {reservation.attendee_count && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {reservation.attendee_count} attendees
                </p>
              )}
            </div>
          </div>

          {/* Purpose */}
          {reservation.purpose && (
            <div className="flex items-start gap-3">
              <FileText className="w-5 h-5 text-lsc-rose mt-0.5" />
              <div>
                <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Purpose</p>
                <p className="text-lsc-dark dark:text-lsc-cream">{reservation.purpose}</p>
              </div>
            </div>
          )}

          {/* Internal Notes */}
          {reservation.internal_notes && (
            <div className="bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg p-3">
              <p className="text-sm font-medium text-status-warning-800 dark:text-status-warning-400 mb-1">
                Internal Notes
              </p>
              <p className="text-sm text-status-warning-700 dark:text-status-warning-300">
                {reservation.internal_notes}
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="pt-4 border-t border-lsc-border dark:border-earth-700 flex flex-wrap gap-2">
            {reservation.status === "pending" && (
              <>
                <button
                  onClick={onApprove}
                  disabled={isApproving}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-status-success-600 hover:bg-status-success-700 text-white rounded-lg text-sm disabled:opacity-50"
                >
                  {isApproving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Check className="w-4 h-4" />} Approve
                </button>
                <button
                  onClick={() => setConfirmRejectOpen(true)}
                  disabled={isApproving}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-lg text-sm disabled:opacity-50"
                >
                  <X className="w-4 h-4" /> Reject
                </button>
              </>
            )}

            {reservation.status === "confirmed" && (
              <>
                <button
                  onClick={onCheckIn}
                  disabled={isCheckingIn}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm disabled:opacity-50"
                >
                  {isCheckingIn ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <LogIn className="w-4 h-4" />} Check In
                </button>
                <button
                  onClick={onCancel}
                  disabled={isCancelling}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-lg text-sm disabled:opacity-50"
                >
                  <XCircle className="w-4 h-4" /> Cancel
                </button>
              </>
            )}

            {!["cancelled", "completed", "no_show", "rejected"].includes(reservation.status) &&
             reservation.status !== "pending" && reservation.status !== "confirmed" && (
              <button
                onClick={onCancel}
                disabled={isCancelling}
                className="flex items-center gap-1.5 px-3 py-1.5 border border-status-danger-300 dark:border-status-danger-700 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded-lg text-sm disabled:opacity-50"
              >
                <XCircle className="w-4 h-4" /> Cancel Reservation
              </button>
            )}

            <button
              onClick={onClose}
              className="ml-auto px-3 py-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg text-sm"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>

    <ConfirmDialog
      open={confirmRejectOpen}
      title={t('reservationDetailModal.confirmRejectTitle', 'Reject reservation?')}
      body={
        <div className="space-y-3">
          <p>
            {t(
              'reservationDetailModal.confirmRejectBody',
              "Reject this reservation for {{patron}}? They'll be notified by email, and this can't be undone."
            ).replace('{{patron}}', patronLabel)}
          </p>
          <div>
            <label
              htmlFor="reject-reason-code"
              className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
            >
              {t('reservationDetailModal.rejectReasonLabel', 'Reason for rejection')}
            </label>
            <select
              id="reject-reason-code"
              value={rejectReasonCode}
              onChange={(e) => setRejectReasonCode(e.target.value as RejectionReasonCode)}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              {REJECTION_REASON_CODES.map(({ value, i18nKey, fallback }) => (
                <option key={value} value={value}>
                  {t(`reservationDetailModal.reasonCode.${i18nKey}`, fallback)}
                </option>
              ))}
            </select>
          </div>
        </div>
      }
      confirmLabel={t('reservationDetailModal.confirmRejectLabel', 'Reject reservation')}
      tone="danger"
      onConfirm={() => {
        setConfirmRejectOpen(false)
        const reason = REJECTION_REASON_CODES.find((r) => r.value === rejectReasonCode)
        onReject(rejectReasonCode, reason?.fallback ?? rejectReasonCode)
      }}
      onCancel={() => setConfirmRejectOpen(false)}
    />
    </>
  )
}
