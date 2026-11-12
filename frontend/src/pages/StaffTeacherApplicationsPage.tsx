/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useState } from 'react'
import { CheckCircle, XCircle, GraduationCap, RefreshCw, Filter } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import {
  approveTeacherApplication,
  denyTeacherApplication,
  listTeacherApplications,
  listTeacherSchools,
  TeacherApplication,
  TeacherApplicationStatus,
  TeacherSchoolOption,
} from '@/api/teacher-applications-api'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

function StatusBadge({ status }: { status: TeacherApplicationStatus }) {
  const styles: Record<TeacherApplicationStatus, string> = {
    pending:
      'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
    approved:
      'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
    denied:
      'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  }
  const labels: Record<TeacherApplicationStatus, string> = {
    pending: 'Pending',
    approved: 'Approved',
    denied: 'Denied',
  }
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}
    >
      {labels[status]}
    </span>
  )
}

interface ReviewModalState {
  application: TeacherApplication
  mode: 'approve' | 'deny'
}

export default function StaffTeacherApplicationsPage(): React.ReactElement {
  const { token } = useAuth()
  const [apps, setApps] = useState<TeacherApplication[]>([])
  const [schools, setSchools] = useState<TeacherSchoolOption[]>([])
  const [statusFilter, setStatusFilter] = useState<TeacherApplicationStatus | ''>(
    'pending'
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modal, setModal] = useState<ReviewModalState | null>(null)
  const [submittingReview, setSubmittingReview] = useState(false)

  const [approveSchoolId, setApproveSchoolId] = useState<number | ''>('')
  const [denyReason, setDenyReason] = useState('')
  const [reviewNotes, setReviewNotes] = useState('')

  const load = useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const [list, schoolList] = await Promise.all([
        listTeacherApplications(token, {
          status: statusFilter || undefined,
          limit: 100,
        }),
        schools.length === 0 ? listTeacherSchools(token) : Promise.resolve(schools),
      ])
      setApps(list.applications)
      if (schools.length === 0) setSchools(schoolList)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [token, statusFilter, schools])

  useEffect(() => {
    void load()
  }, [load])

  const openModal = (application: TeacherApplication, mode: 'approve' | 'deny') => {
    setModal({ application, mode })
    setApproveSchoolId(application.school_id ?? '')
    setDenyReason('')
    setReviewNotes('')
  }

  const closeModal = () => setModal(null)

  const submitReview = async () => {
    if (!modal || !token) return
    setSubmittingReview(true)
    setError(null)
    try {
      if (modal.mode === 'approve') {
        const schoolId =
          typeof approveSchoolId === 'number'
            ? approveSchoolId
            : approveSchoolId === ''
              ? null
              : Number(approveSchoolId)
        await approveTeacherApplication(token, modal.application.id, {
          school_id: schoolId,
          review_notes: reviewNotes || undefined,
        })
      } else {
        if (!denyReason.trim()) {
          setError('Denial reason is required')
          setSubmittingReview(false)
          return
        }
        await denyTeacherApplication(token, modal.application.id, {
          denial_reason: denyReason.trim(),
          review_notes: reviewNotes || undefined,
        })
      }
      closeModal()
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to review')
    } finally {
      setSubmittingReview(false)
    }
  }

  return (
    <AdminShell title="Teacher Applications">
      <main id="main-content" className="p-4 sm:p-6 max-w-6xl mx-auto">
        <header className="mb-6">
          <div className="flex items-center gap-3">
            <GraduationCap className="h-8 w-8 text-blue-700 dark:text-blue-300" aria-hidden />
            <h1 className="text-2xl font-bold">Teacher Applications</h1>
          </div>
          <p className="mt-2 text-sm text-neutral-700 dark:text-neutral-300">
            Review self-serve teacher signups. Approving sets the user&apos;s
            role to TEACHER and links them to a school.
          </p>
        </header>

        <div className="flex flex-wrap items-center gap-3 mb-4">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4" aria-hidden />
            <label htmlFor="teacher-app-status-filter" className="text-sm font-medium">
              Status
            </label>
            <select
              id="teacher-app-status-filter"
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(
                  (e.target.value as TeacherApplicationStatus) || ''
                )
              }
              className="min-h-[44px] rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
            >
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="denied">Denied</option>
            </select>
          </div>
          <button
            type="button"
            onClick={() => void load()}
            className="min-h-[44px] inline-flex items-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-700 px-3 hover:bg-neutral-50 dark:hover:bg-neutral-800 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
          >
            <RefreshCw className="h-4 w-4" aria-hidden /> Refresh
          </button>
        </div>

        {error ? (
          <div
            role="alert"
            className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/10 dark:border-red-900/40 p-4 mb-4"
          >
            <p className="text-sm text-red-900 dark:text-red-100">{error}</p>
          </div>
        ) : null}

        {loading ? (
          <p>Loading…</p>
        ) : apps.length === 0 ? (
          <p className="text-neutral-600 dark:text-neutral-400">
            No applications match the current filter.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <caption className="sr-only">Teacher applications</caption>
              <thead>
                <tr className="text-left border-b border-neutral-200 dark:border-neutral-800">
                  <th className="py-2 pr-3">Applicant</th>
                  <th className="py-2 pr-3">School</th>
                  <th className="py-2 pr-3">Grade / Subject</th>
                  <th className="py-2 pr-3">Submitted</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3 sr-only">Actions</th>
                </tr>
              </thead>
              <tbody>
                {apps.map((a) => (
                  <tr
                    key={a.id}
                    className="border-b border-neutral-100 dark:border-neutral-800"
                  >
                    <td className="py-2 pr-3">
                      <div className="font-medium">{a.user_name || a.user_email}</div>
                      {a.user_name ? (
                        <div className="text-xs text-neutral-600 dark:text-neutral-400">
                          {a.user_email}
                        </div>
                      ) : null}
                    </td>
                    <td className="py-2 pr-3">
                      {a.school_name || a.school_name_freetext || (
                        <span className="text-neutral-500 italic">none</span>
                      )}
                    </td>
                    <td className="py-2 pr-3">
                      {[a.grade_level, a.subject].filter(Boolean).join(' / ') || '—'}
                    </td>
                    <td className="py-2 pr-3 text-xs">
                      {new Date(a.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2 pr-3">
                      <StatusBadge status={a.status} />
                    </td>
                    <td className="py-2 pr-3">
                      {a.status === 'pending' ? (
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => openModal(a, 'approve')}
                            className="min-h-[44px] inline-flex items-center gap-1 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white px-3 text-sm focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2 focus-visible:outline-none"
                          >
                            <CheckCircle className="h-4 w-4" aria-hidden /> Approve
                          </button>
                          <button
                            type="button"
                            onClick={() => openModal(a, 'deny')}
                            className="min-h-[44px] inline-flex items-center gap-1 rounded-lg bg-red-700 hover:bg-red-800 text-white px-3 text-sm focus-visible:ring-2 focus-visible:ring-red-600 focus-visible:ring-offset-2 focus-visible:outline-none"
                          >
                            <XCircle className="h-4 w-4" aria-hidden /> Deny
                          </button>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {modal ? (
          <ModalBackdrop onClose={closeModal} labelledBy="teacher-review-title">
            <div
              className="bg-white dark:bg-neutral-900 rounded-lg p-6 w-full max-w-md"
            >
              <h2 id="teacher-review-title" className="text-lg font-semibold mb-4">
                {modal.mode === 'approve' ? 'Approve' : 'Deny'} application from{' '}
                {modal.application.user_name || modal.application.user_email}
              </h2>
              {modal.mode === 'approve' ? (
                <div className="space-y-3">
                  <label
                    htmlFor="approve-school-select"
                    className="block text-sm font-medium"
                  >
                    Link to school
                  </label>
                  <select
                    id="approve-school-select"
                    value={approveSchoolId}
                    onChange={(e) =>
                      setApproveSchoolId(
                        e.target.value === '' ? '' : Number(e.target.value)
                      )
                    }
                    className="w-full min-h-[44px] rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3"
                  >
                    <option value="">— Pick a school —</option>
                    {schools.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                  {modal.application.school_name_freetext ? (
                    <p className="text-xs text-neutral-600 dark:text-neutral-400">
                      Applicant wrote in: &ldquo;
                      {modal.application.school_name_freetext}
                      &rdquo;
                    </p>
                  ) : null}
                </div>
              ) : (
                <div className="space-y-3">
                  <label
                    htmlFor="deny-reason"
                    className="block text-sm font-medium"
                  >
                    Reason (shared with applicant) *
                  </label>
                  <textarea
                    id="deny-reason"
                    value={denyReason}
                    onChange={(e) => setDenyReason(e.target.value)}
                    rows={3}
                    required
                    className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2"
                  />
                </div>
              )}
              <div className="mt-4">
                <label
                  htmlFor="review-notes"
                  className="block text-sm font-medium"
                >
                  Internal review notes (optional)
                </label>
                <textarea
                  id="review-notes"
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  rows={2}
                  className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2"
                />
              </div>
              <div className="mt-6 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="min-h-[44px] rounded-lg border border-neutral-300 dark:border-neutral-700 px-4 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={submittingReview}
                  onClick={() => void submitReview()}
                  className={`min-h-[44px] rounded-lg px-4 text-white font-medium disabled:opacity-60 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none ${
                    modal.mode === 'approve'
                      ? 'bg-emerald-700 hover:bg-emerald-800 focus-visible:ring-emerald-600'
                      : 'bg-red-700 hover:bg-red-800 focus-visible:ring-red-600'
                  }`}
                >
                  {submittingReview
                    ? 'Saving…'
                    : modal.mode === 'approve'
                      ? 'Approve'
                      : 'Deny'}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        ) : null}
      </main>
    </AdminShell>
  )
}
