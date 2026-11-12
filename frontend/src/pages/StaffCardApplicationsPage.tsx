/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react'
import { CreditCard, Search, CheckCircle, XCircle, Clock, Eye, Filter, RefreshCw, AlertCircle, FileText } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import {
  listCardApplications,
  getCardApplication,
  reviewCardApplication,
  getCardApplicationStats,
  CardApplication,
  CardApplicationStatus,
  CardApplicationStats,
  CardApplicationReview,
} from '@/api/card-applications-api'
import { useTranslation } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

function StatusBadge({ status }: { status: CardApplicationStatus }) {
  const styles = {
    pending: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    under_review: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
    approved: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
    denied: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
  }

  const labels = {
    pending: 'Pending',
    under_review: 'Under Review',
    approved: 'Approved',
    denied: 'Denied',
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  )
}

function StatCard({ title, value, icon: Icon, color }: { title: string; value: number; icon: React.ElementType; color: string }) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{title}</p>
        </div>
      </div>
    </div>
  )
}

export default function StaffCardApplicationsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [applications, setApplications] = useState<CardApplication[]>([])
  const [stats, setStats] = useState<CardApplicationStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<CardApplicationStatus | ''>('')
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const limit = 20

  // Modal state
  const [selectedApplication, setSelectedApplication] = useState<CardApplication | null>(null)
  const [isReviewing, setIsReviewing] = useState(false)
  const [reviewNotes, setReviewNotes] = useState('')
  const [denialReason, setDenialReason] = useState('')
  const [reviewError, setReviewError] = useState('')

  const fetchApplications = async () => {
    if (!token) return
    setIsLoading(true)
    setError('')

    try {
      const response = await listCardApplications(token, {
        ...(statusFilter ? { status: statusFilter } : {}),
        ...(searchQuery ? { search: searchQuery } : {}),
        limit,
        offset,
      })
      setApplications(response.applications)
      setTotal(response.total)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load applications')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchStats = async () => {
    if (!token) return
    try {
      const data = await getCardApplicationStats(token)
      setStats(data)
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    }
  }

  useEffect(() => {
    fetchApplications()
    fetchStats()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, statusFilter, offset])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setOffset(0)
    fetchApplications()
  }

  const openReviewModal = async (applicationId: number) => {
    if (!token) return
    try {
      const app = await getCardApplication(token, applicationId)
      setSelectedApplication(app)
      setReviewNotes('')
      setDenialReason('')
      setReviewError('')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load application')
    }
  }

  const handleReview = async (status: 'under_review' | 'approved' | 'denied') => {
    if (!token || !selectedApplication) return
    setIsReviewing(true)
    setReviewError('')

    try {
      const review: CardApplicationReview = {
        status,
        ...(reviewNotes ? { review_notes: reviewNotes } : {}),
      }
      if (status === 'denied') {
        if (!denialReason.trim()) {
          setReviewError('Please provide a reason for denial')
          setIsReviewing(false)
          return
        }
        review.denial_reason = denialReason
      }

      await reviewCardApplication(token, selectedApplication.id, review)
      setSelectedApplication(null)
      fetchApplications()
      fetchStats()
    } catch (err: unknown) {
      setReviewError(err instanceof Error ? err.message : 'Failed to review application')
    } finally {
      setIsReviewing(false)
    }
  }

  return (

    <AdminShell title="Card Applications">    <PageContainer as="main" width="wide" className="space-y-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-lsc-cream dark:bg-earth-800/30 flex items-center justify-center">
            <CreditCard className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Card Applications
            </h1>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Review and process library card applications
            </p>
          </div>
        </div>
        <button
          onClick={() => { fetchApplications(); fetchStats() }}
          className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-cream dark:bg-earth-700 hover:bg-lsc-cream/80 dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard title="Pending" value={stats.total_pending} icon={Clock} color="bg-status-warning-500" />
          <StatCard title="Under Review" value={stats.total_under_review} icon={Eye} color="bg-earth-500" />
          <StatCard title="Approved" value={stats.total_approved} icon={CheckCircle} color="bg-status-success-500" />
          <StatCard title="Denied" value={stats.total_denied} icon={XCircle} color="bg-status-danger-500" />
        </div>
      )}

      {/* Filters */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
        <div className="flex flex-col md:flex-row gap-4">
          <form onSubmit={handleSearch} className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('staffCardApplications.searchByNameOrEmail')}
                aria-label={t('staffCardApplications.searchByNameOrEmail2')}
                className="w-full pl-10 pr-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors"
            >
              Search
            </button>
          </form>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as CardApplicationStatus | '')
                setOffset(0)
              }}
              aria-label={t('aria.staffCardApplications.filterByStatus', 'Filter by status')}
              className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="under_review">Under Review</option>
              <option value="approved">Approved</option>
              <option value="denied">Denied</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div role="alert" className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
          <p className="text-status-danger-700 dark:text-status-danger-400">{error}</p>
        </div>
      )}

      {/* Applications Table */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="w-8 h-8 border-2 border-lsc-rose border-t-transparent rounded-full motion-safe:animate-spin mx-auto mb-4" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading applications...</p>
          </div>
        ) : applications.length === 0 ? (
          <div className="p-8 text-center">
            <FileText className="w-12 h-12 text-lsc-dark/20 dark:text-lsc-cream/20 mx-auto mb-4" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No applications found</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-lsc-cream dark:bg-lsc-brown">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                      Applicant
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                      Email
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                      Submitted
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {applications.map((app) => (
                    <tr key={app.id} className="hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/50">
                      <td className="px-4 py-4 whitespace-nowrap">
                        <div className="font-medium text-lsc-dark dark:text-lsc-cream">{app.full_name}</div>
                        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{app.city}, {app.state}</div>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-lsc-dark dark:text-lsc-cream">
                        {app.email}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {new Date(app.submitted_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap">
                        <StatusBadge status={app.status} />
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap">
                        <button
                          onClick={() => openReviewModal(app.id)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white text-sm rounded-lg transition-colors"
                        >
                          <Eye className="w-4 h-4" />
                          Review
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {total > limit && (
              <div className="px-4 py-3 border-t border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} applications
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setOffset(Math.max(0, offset - limit))}
                    disabled={offset === 0}
                    className="px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setOffset(offset + limit)}
                    disabled={offset + limit >= total}
                    className="px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Review Modal */}
      {selectedApplication && (
        <ModalBackdrop onClose={() => setSelectedApplication(null)} title="Review Application">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-lg">
            <div className="p-6 border-b border-lsc-border dark:border-earth-700">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                  Review Application #{selectedApplication.id}
                </h2>
                <button
                  onClick={() => setSelectedApplication(null)}
                  aria-label={t('common.close')}
                  className="p-2 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors"
                >
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Applicant Info */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Full Name</h3>
                  <p className="text-lsc-dark dark:text-lsc-cream font-medium">{selectedApplication.full_name}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Email</h3>
                  <p className="text-lsc-dark dark:text-lsc-cream">{selectedApplication.email}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Phone</h3>
                  <p className="text-lsc-dark dark:text-lsc-cream">{selectedApplication.phone || 'Not provided'}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Date of Birth</h3>
                  <p className="text-lsc-dark dark:text-lsc-cream">
                    {selectedApplication.date_of_birth
                      ? new Date(selectedApplication.date_of_birth).toLocaleDateString()
                      : 'Not provided'}
                  </p>
                </div>
              </div>

              {/* Address */}
              <div>
                <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Address</h3>
                <p className="text-lsc-dark dark:text-lsc-cream">
                  {selectedApplication.address_line1}
                  {selectedApplication.address_line2 && <>, {selectedApplication.address_line2}</>}
                  <br />
                  {selectedApplication.city}, {selectedApplication.state} {selectedApplication.zip_code}
                </p>
              </div>

              {/* ID Verification */}
              {selectedApplication.id_type && (
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">ID Type</h3>
                    <p className="text-lsc-dark dark:text-lsc-cream capitalize">{selectedApplication.id_type.replace('_', ' ')}</p>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">ID Last 4</h3>
                    <p className="text-lsc-dark dark:text-lsc-cream font-mono">****{selectedApplication.id_number_last4}</p>
                  </div>
                </div>
              )}

              {/* Current Status */}
              <div className="p-4 bg-lsc-cream dark:bg-lsc-brown rounded-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Current Status</h3>
                    <StatusBadge status={selectedApplication.status} />
                  </div>
                  <div className="text-right">
                    <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Submitted</h3>
                    <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                      {new Date(selectedApplication.submitted_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                {selectedApplication.assigned_card_number && (
                  <div className="mt-4 p-3 bg-status-success-50 dark:bg-status-success-900/20 rounded-lg">
                    <p className="text-sm text-status-success-700 dark:text-status-success-400">
                      Assigned Card: <span className="font-mono font-bold">{selectedApplication.assigned_card_number}</span>
                    </p>
                  </div>
                )}
              </div>

              {/* Review Form */}
              {selectedApplication.status === 'pending' || selectedApplication.status === 'under_review' ? (
                <div className="space-y-4">
                  <div>
                    <label htmlFor="review-notes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                      Review Notes (Optional)
                    </label>
                    <textarea
                      id="review-notes"
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                      rows={3}
                      className="w-full px-4 py-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
                      placeholder={t('staffCardApplications.addNotesAboutThisApplication')}
                    />
                  </div>

                  <div>
                    <label htmlFor="denial-reason" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                      Denial Reason (Required if denying)
                    </label>
                    <textarea
                      id="denial-reason"
                      value={denialReason}
                      onChange={(e) => setDenialReason(e.target.value)}
                      rows={2}
                      className="w-full px-4 py-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
                      placeholder={t('staffCardApplications.reasonForDenyingTheApplication')}
                    />
                  </div>

                  {reviewError && (
                    <div role="alert" className="p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg">
                      <p className="text-sm text-status-danger-700 dark:text-status-danger-400">{reviewError}</p>
                    </div>
                  )}

                  <div className="flex gap-3 pt-4">
                    {selectedApplication.status === 'pending' && (
                      <button
                        onClick={() => handleReview('under_review')}
                        disabled={isReviewing}
                        className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 bg-earth-500 hover:bg-lsc-rose disabled:bg-earth-300 text-white rounded-lg transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                        Mark Under Review
                      </button>
                    )}
                    <button
                      onClick={() => handleReview('approved')}
                      disabled={isReviewing}
                      className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 bg-status-success-500 hover:bg-status-success-600 disabled:bg-status-success-300 text-white rounded-lg transition-colors"
                    >
                      <CheckCircle className="w-4 h-4" />
                      Approve
                    </button>
                    <button
                      onClick={() => handleReview('denied')}
                      disabled={isReviewing}
                      className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 bg-status-danger-500 hover:bg-status-danger-600 disabled:bg-status-danger-300 text-white rounded-lg transition-colors"
                    >
                      <XCircle className="w-4 h-4" />
                      Deny
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-4">
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    This application has already been {selectedApplication.status}.
                  </p>
                </div>
              )}
            </div>
          </div>
        </ModalBackdrop>
      )}
    </PageContainer>
  </AdminShell>
  )
}
