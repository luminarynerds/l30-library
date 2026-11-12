/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useEffect, useState, useCallback } from 'react'
import toast from 'react-hot-toast'
import { CheckCircle2, XCircle, RefreshCw, Calendar } from 'lucide-react'
import { StaffLayout } from './StaffLayout'
import { Button } from '@/components/ui/Button'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { fetchApi } from '@/api/fetchApi'
import { useTranslation } from '@/i18n'

interface VisitRequest {
  id: number
  school_id: number
  school_name: string | null
  teacher_user_id: number | null
  teacher_name: string
  requested_date: string
  scheduled_date: string | null
  number_of_students: number
  grade_level: string
  purpose: string
  status: 'pending' | 'scheduled' | 'rejected' | 'cancelled'
  rejection_reason: string | null
  approved_at: string | null
  created_at: string
}

type ModalState =
  | { kind: 'closed' }
  | { kind: 'approve'; req: VisitRequest; scheduledDate: string; submitting: boolean }
  | { kind: 'reject'; req: VisitRequest; reason: string; submitting: boolean }

const statusBadge: Record<VisitRequest['status'], string> = {
  pending:
    'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200',
  scheduled:
    'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200',
  rejected:
    'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-900 dark:text-status-danger-200',
  cancelled:
    'bg-earth-100 dark:bg-earth-800/30 text-earth-900 dark:text-lsc-cream/80',
}

const formatDate = (iso: string | null): string => {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export const StaffLibraryVisitsPage: React.FC = () => {
  const { t } = useTranslation()
  const [requests, setRequests] = useState<VisitRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [modal, setModal] = useState<ModalState>({ kind: 'closed' })

  const fetchRequests = useCallback(async () => {
    try {
      const data = await fetchApi(`/school-partnerships/library-visits/requests`)
      setRequests(Array.isArray(data?.requests) ? data.requests : [])
    } catch (err) {
      Sentry.captureException(err)
      toast.error(t('components.staff.staffLibraryVisits.loadFailed'))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [t])

  useEffect(() => {
    fetchRequests()
  }, [fetchRequests])

  const handleRefresh = () => {
    setRefreshing(true)
    fetchRequests()
  }

  const openApprove = (req: VisitRequest) => {
    // Default scheduled_date to the teacher's requested date (datetime-local format).
    const requested = req.requested_date ? req.requested_date.slice(0, 16) : ''
    setModal({ kind: 'approve', req, scheduledDate: requested, submitting: false })
  }

  const openReject = (req: VisitRequest) => {
    setModal({ kind: 'reject', req, reason: '', submitting: false })
  }

  const closeModal = () => setModal({ kind: 'closed' })

  const submitApprove = async () => {
    if (modal.kind !== 'approve') return
    if (!modal.scheduledDate) {
      toast.error(t('components.staff.staffLibraryVisits.scheduledDateRequired'))
      return
    }
    setModal({ ...modal, submitting: true })
    try {
      const iso = new Date(modal.scheduledDate).toISOString()
      await fetchApi(
        `/school-partnerships/library-visits/requests/${modal.req.id}/approve`,
        {
          method: 'POST',
          body: JSON.stringify({ scheduledDate: iso }),
        },
      )
      toast.success(t('components.staff.staffLibraryVisits.approvedToast'))
      closeModal()
      await fetchRequests()
    } catch (err) {
      Sentry.captureException(err)
      toast.error(t('components.staff.staffLibraryVisits.approveFailed'))
      setModal({ ...modal, submitting: false })
    }
  }

  const submitReject = async () => {
    if (modal.kind !== 'reject') return
    if (!modal.reason.trim()) {
      toast.error(t('components.staff.staffLibraryVisits.reasonRequired'))
      return
    }
    setModal({ ...modal, submitting: true })
    try {
      await fetchApi(
        `/school-partnerships/library-visits/requests/${modal.req.id}/reject`,
        {
          method: 'POST',
          body: JSON.stringify({ reason: modal.reason.trim() }),
        },
      )
      toast.success(t('components.staff.staffLibraryVisits.rejectedToast'))
      closeModal()
      await fetchRequests()
    } catch (err) {
      Sentry.captureException(err)
      toast.error(t('components.staff.staffLibraryVisits.rejectFailed'))
      setModal({ ...modal, submitting: false })
    }
  }

  const pending = requests.filter((r) => r.status === 'pending')
  const recent = requests.filter((r) => r.status !== 'pending').slice(0, 25)

  return (
    <StaffLayout
      title={t('components.staff.staffLibraryVisits.title')}
      subtitle={t('components.staff.staffLibraryVisits.subtitle')}
      loading={loading}
      actions={
        <Button
          variant="secondary"
          onClick={handleRefresh}
          disabled={refreshing}
          aria-label={t('components.staff.staffLibraryVisits.refresh')}
        >
          <RefreshCw
            className={`w-4 h-4 mr-2 ${refreshing ? 'motion-safe:animate-spin' : ''}`}
            aria-hidden
          />
          {t('components.staff.staffLibraryVisits.refresh')}
        </Button>
      }
    >
      <section
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6"
        aria-labelledby="pending-heading"
      >
        <h2
          id="pending-heading"
          className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4"
        >
          {t('components.staff.staffLibraryVisits.pendingHeading', { count: pending.length })}
        </h2>

        {pending.length === 0 ? (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 py-6 text-center">
            {t('components.staff.staffLibraryVisits.noPending')}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="pending-table">
              <thead>
                <tr className="text-left border-b border-earth-200 dark:border-earth-700">
                  <th className="py-2 pr-3">
                    {t('components.staff.staffLibraryVisits.colTeacher')}
                  </th>
                  <th className="py-2 pr-3">
                    {t('components.staff.staffLibraryVisits.colSchool')}
                  </th>
                  <th className="py-2 pr-3">
                    {t('components.staff.staffLibraryVisits.colRequested')}
                  </th>
                  <th className="py-2 pr-3">
                    {t('components.staff.staffLibraryVisits.colStudents')}
                  </th>
                  <th className="py-2 pr-3">
                    {t('components.staff.staffLibraryVisits.colGrade')}
                  </th>
                  <th className="py-2 pr-3">
                    {t('components.staff.staffLibraryVisits.colPurpose')}
                  </th>
                  <th className="py-2 pr-3 text-right">
                    {t('components.staff.staffLibraryVisits.colActions')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {pending.map((req) => (
                  <tr
                    key={req.id}
                    className="border-b border-earth-100 dark:border-earth-700/50 align-top"
                    data-testid={`pending-row-${req.id}`}
                  >
                    <td className="py-3 pr-3 font-medium text-lsc-dark dark:text-lsc-cream">
                      {req.teacher_name}
                    </td>
                    <td className="py-3 pr-3 text-lsc-dark/80 dark:text-lsc-cream/80">
                      {req.school_name || `#${req.school_id}`}
                    </td>
                    <td className="py-3 pr-3 text-lsc-dark/80 dark:text-lsc-cream/80">
                      {formatDate(req.requested_date)}
                    </td>
                    <td className="py-3 pr-3 text-lsc-dark/80 dark:text-lsc-cream/80">
                      {req.number_of_students}
                    </td>
                    <td className="py-3 pr-3 text-lsc-dark/80 dark:text-lsc-cream/80">
                      {req.grade_level}
                    </td>
                    <td className="py-3 pr-3 text-lsc-dark/80 dark:text-lsc-cream/80 max-w-xs">
                      <span className="line-clamp-2">{req.purpose}</span>
                    </td>
                    <td className="py-3 pr-3">
                      <div className="flex gap-2 justify-end">
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => openApprove(req)}
                          data-testid={`approve-${req.id}`}
                        >
                          <CheckCircle2 className="w-4 h-4 mr-1" aria-hidden />
                          {t('components.staff.staffLibraryVisits.approve')}
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => openReject(req)}
                          data-testid={`reject-${req.id}`}
                        >
                          <XCircle className="w-4 h-4 mr-1" aria-hidden />
                          {t('components.staff.staffLibraryVisits.reject')}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6"
        aria-labelledby="recent-heading"
      >
        <h2
          id="recent-heading"
          className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4"
        >
          {t('components.staff.staffLibraryVisits.recentHeading')}
        </h2>
        {recent.length === 0 ? (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 py-6 text-center">
            {t('components.staff.staffLibraryVisits.noRecent')}
          </p>
        ) : (
          <ul className="divide-y divide-earth-200 dark:divide-earth-700">
            {recent.map((req) => (
              <li key={req.id} className="py-3 flex flex-wrap items-center gap-3">
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-semibold ${statusBadge[req.status]}`}
                >
                  {req.status}
                </span>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                  {req.teacher_name}
                </span>
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  {req.school_name || `#${req.school_id}`}
                </span>
                {req.scheduled_date && (
                  <span className="text-lsc-dark/80 dark:text-lsc-cream/80 inline-flex items-center gap-1">
                    <Calendar className="w-4 h-4" aria-hidden />
                    {formatDate(req.scheduled_date)}
                  </span>
                )}
                {req.rejection_reason && (
                  <span className="text-status-danger-900 dark:text-status-danger-200 text-xs italic">
                    {req.rejection_reason}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {modal.kind === 'approve' && (
        <ModalBackdrop onClose={modal.submitting ? undefined : closeModal}>
          <div
            className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 max-w-md w-full"
            role="dialog"
            aria-labelledby="approve-modal-title"
          >
            <h3
              id="approve-modal-title"
              className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-3"
            >
              {t('components.staff.staffLibraryVisits.approveModalTitle')}
            </h3>
            <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mb-4">
              {t('components.staff.staffLibraryVisits.approveModalBody', {
                teacher: modal.req.teacher_name,
                school: modal.req.school_name || `#${modal.req.school_id}`,
              })}
            </p>
            <label className="block mb-4">
              <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                {t('components.staff.staffLibraryVisits.scheduledDateLabel')}
              </span>
              <input
                type="datetime-local"
                value={modal.scheduledDate}
                onChange={(e) =>
                  setModal({ ...modal, scheduledDate: e.target.value })
                }
                className="w-full rounded border border-earth-300 dark:border-earth-600 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream px-3 py-2"
                data-testid="approve-date-input"
                required
              />
            </label>
            <div className="flex justify-end gap-2">
              <Button
                variant="tertiary"
                onClick={closeModal}
                disabled={modal.submitting}
              >
                {t('components.staff.staffLibraryVisits.cancel')}
              </Button>
              <Button
                variant="primary"
                onClick={submitApprove}
                disabled={modal.submitting}
                data-testid="approve-submit"
              >
                {modal.submitting
                  ? t('components.staff.staffLibraryVisits.submitting')
                  : t('components.staff.staffLibraryVisits.confirmApprove')}
              </Button>
            </div>
          </div>
        </ModalBackdrop>
      )}

      {modal.kind === 'reject' && (
        <ModalBackdrop onClose={modal.submitting ? undefined : closeModal}>
          <div
            className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 max-w-md w-full"
            role="dialog"
            aria-labelledby="reject-modal-title"
          >
            <h3
              id="reject-modal-title"
              className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-3"
            >
              {t('components.staff.staffLibraryVisits.rejectModalTitle')}
            </h3>
            <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mb-4">
              {t('components.staff.staffLibraryVisits.rejectModalBody', {
                teacher: modal.req.teacher_name,
              })}
            </p>
            <label className="block mb-4">
              <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                {t('components.staff.staffLibraryVisits.reasonLabel')}
              </span>
              <textarea
                value={modal.reason}
                onChange={(e) => setModal({ ...modal, reason: e.target.value })}
                rows={4}
                maxLength={1000}
                className="w-full rounded border border-earth-300 dark:border-earth-600 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream px-3 py-2"
                data-testid="reject-reason-input"
                required
              />
            </label>
            <div className="flex justify-end gap-2">
              <Button
                variant="tertiary"
                onClick={closeModal}
                disabled={modal.submitting}
              >
                {t('components.staff.staffLibraryVisits.cancel')}
              </Button>
              <Button
                variant="danger"
                onClick={submitReject}
                disabled={modal.submitting}
                data-testid="reject-submit"
              >
                {modal.submitting
                  ? t('components.staff.staffLibraryVisits.submitting')
                  : t('components.staff.staffLibraryVisits.confirmReject')}
              </Button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </StaffLayout>
  )
}

export default StaffLibraryVisitsPage
