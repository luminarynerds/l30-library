/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { Link } from "react-router-dom"
import { useAuth } from "@/contexts/AuthContext"
import { fetchApi } from "@/api/fetchApi"
import { SectionShell } from "../ai-settings/SectionShell"
import {
  FileText,
  Search,
  RefreshCw,
  Loader2,
  Plus,
  Clock,
  CheckCircle,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  X,
  Save,
  Calendar,
  Mail,
  User,
} from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation, getCurrentLocale } from "@/i18n"
import FocusTrap from 'focus-trap-react'

interface PublicRecordsRequest {
  id: number
  tracking_number: string
  requester_name: string
  requester_email?: string
  requester_organization?: string
  request_type: string
  description: string
  status: string
  date_received: string
  date_due?: string
  date_completed?: string
  assigned_to_id?: number
  assigned_to_name?: string
  response_format?: string
  estimated_fee?: number
  fee_paid?: number
  created_at: string
  meeting_id?: number | null
  committee_id?: number | null
}

interface PublicRecordsStats {
  year: number
  total_requests: number
  pending: number
  completed: number
  denied: number
  partially_denied: number
  withdrawn: number
  appealed: number
}

interface PublicRecordsSectionProps {
  onBack: () => void
}

const TABS = [{ id: "requests", label: "Requests", icon: FileText }] as const

export function PublicRecordsSection({ onBack }: PublicRecordsSectionProps) {
  const { t } = useTranslation()
  const { token } = useAuth()

  const [isLoading, setIsLoading] = useState(true)
  const [requests, setRequests] = useState<PublicRecordsRequest[]>([])
  const [stats, setStats] = useState<PublicRecordsStats | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [showCreateModal, setShowCreateModal] = useState(false)
  const todayISO = () => new Date().toISOString().slice(0, 10)
  const [newRequest, setNewRequest] = useState({
    requester_name: "",
    requester_email: "",
    requester_organization: "",
    request_type: "general",
    jurisdiction: "ohio",
    date_received: todayISO(),
    description: "",
    response_format: "electronic",
  })

  const pageSize = 20

  const fetchRequests = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * pageSize),
        limit: String(pageSize),
      })
      if (statusFilter) params.set("status", statusFilter)

      const data = await fetchApi(`/public-records?${params}`)
      setRequests(data.items || [])
      setTotalPages(Math.ceil((data.total || 0) / pageSize))
    } catch (_error: unknown) {
      toast.error(t("admin.adminPublicRecords.failedToLoadPublicRecords"))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, page, statusFilter])

  const fetchStats = useCallback(async () => {
    if (!token) return
    try {
      const year = new Date().getFullYear()
      const data = await fetchApi(`/public-records/statistics/${year}`)
      setStats(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [token])

  useEffect(() => {
    if (token) {
      fetchRequests()
      fetchStats()
    }
  }, [token, fetchRequests, fetchStats])

  const handleCreateRequest = async () => {
    if (!token || !newRequest.requester_name || !newRequest.description || !newRequest.date_received) {
      toast.error(t("admin.adminPublicRecords.nameAndDescriptionAreRequired"))
      return
    }
    if (newRequest.description.trim().length < 10) {
      toast.error(t("admin.adminPublicRecords.descriptionMinLength"))
      return
    }
    try {
      await fetchApi('/public-records', {
        method: "POST",
        body: JSON.stringify({
          requester_name: newRequest.requester_name,
          requester_email: newRequest.requester_email || undefined,
          requester_organization: newRequest.requester_organization || undefined,
          request_type: newRequest.request_type,
          jurisdiction: newRequest.jurisdiction,
          date_received: new Date(newRequest.date_received).toISOString(),
          description: newRequest.description,
          preferred_format: newRequest.response_format,
        }),
      })
      toast.success(t("toast.adminLawEnforcement.requestCreatedSuccessfully"))
      setShowCreateModal(false)
      setNewRequest({
        requester_name: "",
        requester_email: "",
        requester_organization: "",
        request_type: "general",
        jurisdiction: "ohio",
        date_received: todayISO(),
        description: "",
        response_format: "electronic",
      })
      fetchRequests()
      fetchStats()
    } catch (_error: unknown) {
      toast.error(t("admin.adminPublicRecords.failedToCreateRequest"))
    }
  }

  const handleUpdateStatus = async (requestId: number, newStatus: string) => {
    if (!token) return
    try {
      await fetchApi(`/public-records/${requestId}/status`, {
        method: "POST",
        body: JSON.stringify({ status: newStatus }),
      })
      toast.success(t("toast.adminMaterialCosts.statusUpdated"))
      fetchRequests()
      fetchStats()
    } catch (_error: unknown) {
      toast.error(t("admin.adminPublicRecords.failedToUpdateStatus"))
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return "text-status-success-600 dark:text-status-success-400 bg-status-success-100 dark:bg-status-success-900/30"
      case "pending":
      case "received":
        return "text-status-warning-600 dark:text-status-warning-400 bg-status-warning-100 dark:bg-status-warning-900/30"
      case "in_progress":
        return "text-lsc-rose dark:text-lsc-rose-light bg-earth-100 dark:bg-earth-800/30"
      case "denied":
        return "text-status-danger-600 dark:text-status-danger-400 bg-status-danger-100 dark:bg-status-danger-900/30"
      default:
        return "text-lsc-dark/70 dark:text-lsc-cream/70 bg-earth-100 dark:bg-earth-700"
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  return (
    <SectionShell
      title="Public Records Requests"
      description="Manage public records requests. Track deadlines and maintain response documentation."
      tabs={[...TABS]}
      onBack={onBack}
    >
      {() => (
        <div className="space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h3 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Public Records Requests
              </h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Manage FOIA and public records requests
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  fetchRequests()
                  fetchStats()
                }}
                className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
              >
                <Plus className="w-4 h-4" />
                New Request
              </button>
            </div>
          </div>

          {/* Stats Grid */}
          {stats && (
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <FileText className="w-4 h-4" />
                  <span className="text-xs font-semibold">Total ({stats.year})</span>
                </div>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {stats.total_requests}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <Clock className="w-4 h-4" />
                  <span className="text-xs font-semibold">Pending</span>
                </div>
                <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">
                  {stats.pending}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-xs font-semibold">Completed</span>
                </div>
                <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">
                  {stats.completed}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-xs font-semibold">Denied</span>
                </div>
                <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">
                  {stats.denied + stats.partially_denied}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <Search className="w-4 h-4" />
                  <span className="text-xs font-semibold">Appealed</span>
                </div>
                <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                  {stats.appealed}
                </p>
              </div>
            </div>
          )}

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-4">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(1)
              }}
              aria-label={t("admin.adminPublicRecords.filterByRequestStatus")}
              className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="denied">Denied</option>
            </select>
          </div>

          {/* Requests List */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : requests.length === 0 ? (
              <div className="p-8 text-center">
                <FileText className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                  No Requests Found
                </h3>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  No public records requests match your criteria.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-lsc-border dark:divide-earth-700">
                {requests.map((request) => (
                  <div key={request.id} className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {request.tracking_number}
                          </span>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getStatusColor(request.status)}`}>
                            {request.status.replace(/_/g, " ")}
                          </span>
                        </div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                          {request.description}
                        </p>
                        <div className="flex flex-wrap items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          <span className="flex items-center gap-1">
                            <User className="w-3 h-3" />
                            {request.requester_name}
                          </span>
                          {request.requester_email && (
                            <span className="flex items-center gap-1">
                              <Mail className="w-3 h-3" />
                              {request.requester_email}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            Received: {formatDate(request.date_received)}
                          </span>
                          {request.date_due && (
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              Due: {formatDate(request.date_due)}
                            </span>
                          )}
                          {request.meeting_id && (
                            <Link
                              to={`/admin/board/meetings/${request.meeting_id}`}
                              className="flex items-center gap-1 text-blue-600 dark:text-blue-400 underline hover:opacity-80"
                            >
                              From meeting #{request.meeting_id}
                            </Link>
                          )}
                          {request.committee_id && (
                            <Link
                              to={`/admin/board/committees/${request.committee_id}`}
                              className="flex items-center gap-1 text-blue-600 dark:text-blue-400 underline hover:opacity-80"
                            >
                              From committee #{request.committee_id}
                            </Link>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {request.status === "pending" && (
                          <button
                            onClick={() => handleUpdateStatus(request.id, "in_progress")}
                            className="px-3 py-1.5 text-sm text-lsc-rose dark:text-lsc-rose-light hover:bg-earth-50 dark:bg-earth-800/20 dark:hover:bg-earth-800/20 rounded-lg"
                          >
                            Start
                          </button>
                        )}
                        {request.status === "in_progress" && (
                          <button
                            onClick={() => handleUpdateStatus(request.id, "completed")}
                            className="px-3 py-1.5 text-sm text-status-success-600 dark:text-status-success-400 hover:bg-status-success-50 dark:bg-status-success-900/20 dark:hover:bg-status-success-900/20 rounded-lg"
                          >
                            Complete
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-lsc-border dark:border-earth-700">
                <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Page {page} of {totalPages}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    aria-label="Previous page"
                    className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page === totalPages}
                    aria-label="Next page"
                    className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Create Modal */}
          {showCreateModal && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onKeyDown={(e) => { if (e.key === "Escape") setShowCreateModal(false); }}>
              <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
              <div role="dialog" aria-modal="true" aria-labelledby="pr-modal-title" className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full max-h-[90vh] overflow-auto">
                <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                  <h3 id="pr-modal-title" className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                    Log New Public Records Request
                  </h3>
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="p-4 space-y-4">
                  <div>
                    <label htmlFor="pr-requester-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                      Requester Name <span className="text-status-danger-500">*</span>
                    </label>
                    <input
                      id="pr-requester-name"
                      type="text"
                      value={newRequest.requester_name}
                      onChange={(e) => setNewRequest({ ...newRequest, requester_name: e.target.value })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="pr-requester-email" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                        Email
                      </label>
                      <input
                        id="pr-requester-email"
                        type="email"
                        value={newRequest.requester_email}
                        onChange={(e) => setNewRequest({ ...newRequest, requester_email: e.target.value })}
                        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                    <div>
                      <label htmlFor="pr-requester-org" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                        Organization
                      </label>
                      <input
                        id="pr-requester-org"
                        type="text"
                        value={newRequest.requester_organization}
                        onChange={(e) => setNewRequest({ ...newRequest, requester_organization: e.target.value })}
                        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="pr-request-type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                        Request Type
                      </label>
                      <select
                        id="pr-request-type"
                        value={newRequest.request_type}
                        onChange={(e) => setNewRequest({ ...newRequest, request_type: e.target.value })}
                        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                      >
                        <option value="general">General Request</option>
                        <option value="financial">Financial Records</option>
                        <option value="personnel">Personnel Records</option>
                        <option value="policy">Policy Documents</option>
                        <option value="statistics">Statistics</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="pr-response-format" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                        Response Format
                      </label>
                      <select
                        id="pr-response-format"
                        value={newRequest.response_format}
                        onChange={(e) => setNewRequest({ ...newRequest, response_format: e.target.value })}
                        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                      >
                        <option value="electronic">Electronic</option>
                        <option value="paper">Paper Copy</option>
                        <option value="inspect">Inspection Only</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label htmlFor="pr-jurisdiction" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                      {t("admin.adminPublicRecords.jurisdiction")} <span className="text-status-danger-500">*</span>
                    </label>
                    <select
                      id="pr-jurisdiction"
                      value={newRequest.jurisdiction}
                      onChange={(e) => setNewRequest({ ...newRequest, jurisdiction: e.target.value })}
                      aria-label={t("admin.adminPublicRecords.jurisdiction")}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                    >
                      <option value="federal">Federal (FOIA)</option>
                      <option value="california">California</option>
                      <option value="texas">Texas</option>
                      <option value="new_york">New York</option>
                      <option value="florida">Florida</option>
                      <option value="illinois">Illinois</option>
                      <option value="pennsylvania">Pennsylvania</option>
                      <option value="ohio">Ohio</option>
                      <option value="georgia">Georgia</option>
                      <option value="michigan">Michigan</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor="pr-date-received" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                      Date Received <span className="text-status-danger-500">*</span>
                    </label>
                    <input
                      id="pr-date-received"
                      type="date"
                      value={newRequest.date_received}
                      onChange={(e) => setNewRequest({ ...newRequest, date_received: e.target.value })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <div>
                    <label htmlFor="pr-description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                      Description <span className="text-status-danger-500">*</span>
                    </label>
                    <textarea
                      id="pr-description"
                      value={newRequest.description}
                      onChange={(e) => setNewRequest({ ...newRequest, description: e.target.value })}
                      rows={4}
                      minLength={10}
                      placeholder={t("admin.adminPublicRecords.describeTheRecordsBeingRequested")}
                      aria-describedby="pr-description-hint"
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                    />
                    <p id="pr-description-hint" className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      Minimum 10 characters.
                    </p>
                  </div>
                </div>
                <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCreateRequest}
                    className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
                  >
                    <Save className="w-4 h-4" />
                    Create Request
                  </button>
                </div>
              </div>
              </FocusTrap>
            </div>
          )}
        </div>
      )}
    </SectionShell>
  )
}
