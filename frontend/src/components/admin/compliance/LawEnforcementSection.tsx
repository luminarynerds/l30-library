/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { fetchApi } from "@/api/fetchApi"
import {
  Shield,
  FileText,
  CheckCircle,
  RefreshCw,
  Loader2,
  Plus,
  Eye,
  Clock,
  Scale,
  BarChart3,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation, getCurrentLocale } from "@/i18n"
import type {
  LawEnforcementRequest,
  LawEnforcementRequestDetail,
  ChecklistItem,
  AuditLogEntry,
  LEStats,
  WorkflowActionType,
} from "@/components/law-enforcement/types"
import { CreateRequestModal } from "@/components/law-enforcement/CreateRequestModal"
import { WorkflowActionModal } from "@/components/law-enforcement/WorkflowActionModal"
import { DetailPanel } from "@/components/law-enforcement/DetailPanel"
import { SectionShell } from "../ai-settings/SectionShell"

interface LawEnforcementSectionProps {
  onBack: () => void
}

export function LawEnforcementSection({ onBack }: LawEnforcementSectionProps) {
  const { t } = useTranslation()
  const { token, isAuthenticated } = useAuth()

  const [isLoading, setIsLoading] = useState(true)
  const [requests, setRequests] = useState<LawEnforcementRequest[]>([])
  const [stats, setStats] = useState<LEStats | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [typeFilter, setTypeFilter] = useState("")
  const [yearFilter, setYearFilter] = useState(new Date().getFullYear().toString())

  const [selectedRequest, setSelectedRequest] = useState<LawEnforcementRequestDetail | null>(null)
  const [showDetailPanel, setShowDetailPanel] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailTab, setDetailTab] = useState<"overview" | "checklist" | "audit">("overview")
  const [checklist, setChecklist] = useState<ChecklistItem[]>([])
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([])

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showWorkflowModal, setShowWorkflowModal] = useState(false)

  const [newRequest, setNewRequest] = useState({
    requesting_agency: "",
    request_type: "subpoena",
    date_received: new Date().toISOString().split("T")[0] ?? "",
    data_requested: "",
    patron_name_on_request: "",
    requesting_officer_name: "",
    requesting_officer_badge: "",
    description: "",
  })

  const [workflowAction, setWorkflowAction] = useState<{
    action: WorkflowActionType
    data: Record<string, unknown>
  } | null>(null)
  const [noteText, setNoteText] = useState("")

  const pageSize = 20

  const fetchRequests = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * pageSize),
        limit: String(pageSize),
      })
      if (statusFilter) params.set("workflow_status", statusFilter)
      if (typeFilter) params.set("request_type", typeFilter)
      if (yearFilter) params.set("year", yearFilter)

      const data = await fetchApi(`/law-enforcement/requests?${params}`)
      setRequests(data.items || [])
      setTotalPages(Math.ceil((data.total || 0) / pageSize))
    } catch (_error: unknown) {
      toast.error(t("admin.adminLawEnforcement.failedToLoadLawEnforcement"))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, page, statusFilter, typeFilter, yearFilter])

  const fetchStats = useCallback(async () => {
    if (!token) return
    try {
      const data = await fetchApi('/law-enforcement/stats')
      setStats(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [token])

  const fetchRequestDetail = useCallback(
    async (requestId: number) => {
      if (!token) return
      setDetailLoading(true)
      try {
        const data = await fetchApi(`/law-enforcement/requests/${requestId}`)
        setSelectedRequest(data)
      } catch (_error: unknown) {
        toast.error(t("admin.adminLawEnforcement.failedToLoadRequestDetails"))
      } finally {
        setDetailLoading(false)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [token]
  )

  const fetchChecklist = useCallback(
    async (requestId: number) => {
      if (!token) return
      try {
        const data = await fetchApi(`/law-enforcement/requests/${requestId}/checklist`)
        setChecklist(Array.isArray(data) ? data : data.items || [])
      } catch (_error: unknown) {
        toast.error(t("admin.adminLawEnforcement.failedToLoadChecklist"))
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [token]
  )

  const fetchAuditLog = useCallback(
    async (requestId: number) => {
      if (!token) return
      try {
        const data = await fetchApi(`/law-enforcement/requests/${requestId}/audit-log`)
        setAuditLog(Array.isArray(data) ? data : data.items || [])
      } catch (_error: unknown) {
        toast.error(t("admin.adminLawEnforcement.failedToLoadAuditLog"))
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [token]
  )

  useEffect(() => {
    if (token && isAuthenticated) {
      fetchRequests()
      fetchStats()
    }
  }, [token, isAuthenticated, fetchRequests, fetchStats])

  const handleCreateRequest = async () => {
    if (!token || !newRequest.requesting_agency || !newRequest.date_received || !newRequest.data_requested) {
      toast.error(t("admin.adminLawEnforcement.agencyDateReceivedAndData"))
      return
    }
    // The backend schema (StrictInputSchema, extra="forbid") accepts
    // agency_contact_name + internal_notes but has no columns for
    // officer name/badge/description. Fold the modal's officer + description
    // inputs into those two fields so the request validates.
    const notesParts: string[] = []
    if (newRequest.requesting_officer_badge) {
      notesParts.push(`Officer badge: ${newRequest.requesting_officer_badge}`)
    }
    if (newRequest.description) {
      notesParts.push(newRequest.description)
    }
    try {
      await fetchApi('/law-enforcement/requests', {
        method: "POST",
        body: JSON.stringify({
          requesting_agency: newRequest.requesting_agency,
          request_type: newRequest.request_type,
          date_received: newRequest.date_received,
          data_requested: newRequest.data_requested,
          patron_name_on_request: newRequest.patron_name_on_request || undefined,
          agency_contact_name: newRequest.requesting_officer_name || undefined,
          internal_notes: notesParts.length ? notesParts.join('\n') : undefined,
        }),
      })
      toast.success(t("toast.adminLawEnforcement.requestCreatedSuccessfully"))
      setShowCreateModal(false)
      setNewRequest({
        requesting_agency: "",
        request_type: "subpoena",
        date_received: new Date().toISOString().split("T")[0] ?? "",
        data_requested: "",
        patron_name_on_request: "",
        requesting_officer_name: "",
        requesting_officer_badge: "",
        description: "",
      })
      fetchRequests()
      fetchStats()
    } catch (_error: unknown) {
      toast.error(t("admin.adminLawEnforcement.failedToCreateRequest"))
    }
  }

  const openDetailPanel = async (request: LawEnforcementRequest) => {
    setSelectedRequest(null)
    setShowDetailPanel(true)
    setDetailTab("overview")
    await fetchRequestDetail(request.id)
    await fetchChecklist(request.id)
    await fetchAuditLog(request.id)
  }

  const handleWorkflowAction = async (
    action: WorkflowActionType,
    data: Record<string, unknown>
  ) => {
    if (!token || !selectedRequest) return
    try {
      await fetchApi(`/law-enforcement/requests/${selectedRequest.id}/${action.replace(/_/g, "-")}`, {
        method: "POST",
        body: JSON.stringify(data),
      })
      toast.success(t("toast.adminLawEnforcement.replacegCompletedSuccessfully", { replaceg: action.replace(/_/g, " ") }))
      setShowWorkflowModal(false)
      setWorkflowAction(null)
      setNoteText("")
      await fetchRequestDetail(selectedRequest.id)
      await fetchAuditLog(selectedRequest.id)
      fetchRequests()
      fetchStats()
    } catch (_error: unknown) {
      toast.error(t("admin.adminLawEnforcement.failedToPerformWorkflowAction"))
    }
  }

  const handleChecklistToggle = async (itemId: number, completed: boolean) => {
    if (!token || !selectedRequest) return
    try {
      const updatedItem = await fetchApi(
        `/law-enforcement/requests/${selectedRequest.id}/checklist/${itemId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ completed }),
        }
      )
      setChecklist(checklist.map((item) => (item.id === itemId ? updatedItem : item)))
      toast.success(completed ? t("toast.adminLawEnforcement.itemCompleted") : t("toast.adminLawEnforcement.itemMarkedIncomplete"))
      await fetchAuditLog(selectedRequest.id)
    } catch (_error: unknown) {
      toast.error(t("admin.adminLawEnforcement.failedToUpdateChecklistItem"))
    }
  }

  const handleAddNote = async () => {
    if (!token || !selectedRequest || !noteText.trim()) {
      toast.error(t("admin.adminLawEnforcement.noteTextIsRequired"))
      return
    }
    try {
      await fetchApi(
        `/law-enforcement/requests/${selectedRequest.id}/notes`,
        {
          method: "POST",
          body: JSON.stringify({ content: noteText }),
        }
      )
      toast.success(t("toast.adminLawEnforcement.noteAddedSuccessfully"))
      setNoteText("")
      await fetchAuditLog(selectedRequest.id)
    } catch (_error: unknown) {
      toast.error(t("admin.adminLawEnforcement.failedToAddNote"))
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
      case "response_sent":
        return "text-status-success-600 dark:text-status-success-400 bg-status-success-100 dark:bg-status-success-900/30"
      case "pending_review":
      case "received":
        return "text-status-warning-600 dark:text-status-warning-400 bg-status-warning-100 dark:bg-status-warning-900/30"
      case "rejected":
        return "text-status-danger-600 dark:text-status-danger-400 bg-status-danger-100 dark:bg-status-danger-900/30"
      default:
        return "text-lsc-rose dark:text-lsc-rose-light bg-earth-100 dark:bg-earth-800/30"
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  const tabs = [{ id: "requests", label: "Requests", icon: Scale }]

  return (
    <SectionShell
      title="Law Enforcement Requests"
      description="Track and respond to law enforcement requests for patron records. Every request is logged."
      tabs={tabs}
      onBack={onBack}
    >
      {() => (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-end gap-3">
            <button
              onClick={() => { fetchRequests(); fetchStats() }}
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

          {stats && (
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <FileText className="w-4 h-4" />
                  <span className="text-xs uppercase">Total</span>
                </div>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats.total_requests}</p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <Clock className="w-4 h-4" />
                  <span className="text-xs uppercase">Pending Review</span>
                </div>
                <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">{stats.pending_review}</p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <Scale className="w-4 h-4" />
                  <span className="text-xs uppercase">In Progress</span>
                </div>
                <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{stats.in_progress}</p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-xs uppercase">Completed</span>
                </div>
                <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">{stats.completed}</p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <BarChart3 className="w-4 h-4" />
                  <span className="text-xs uppercase">This Year</span>
                </div>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats.this_year}</p>
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-4">
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
              aria-label={t("admin.adminLawEnforcement.filterByRequestStatus")}
              className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            >
              <option value="">All Statuses</option>
              <option value="received">Received</option>
              <option value="validating">Validating</option>
              <option value="legal_review">Legal Review</option>
              <option value="preparing_response">Preparing Response</option>
              <option value="completed">Completed</option>
              <option value="rejected">Rejected</option>
            </select>

            <select
              value={typeFilter}
              onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}
              aria-label={t("admin.adminLawEnforcement.filterByRequestType")}
              className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            >
              <option value="">All Types</option>
              <option value="subpoena">Subpoena</option>
              <option value="warrant">Warrant</option>
              <option value="court_order">Court Order</option>
              <option value="informal">Informal Request</option>
              <option value="national_security_letter">National Security Letter</option>
            </select>

            <select
              value={yearFilter}
              onChange={(e) => { setYearFilter(e.target.value); setPage(1) }}
              aria-label={t("aria.adminLawEnforcement.filterByYear")}
              className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            >
              {Array.from({ length: 3 }, (_, i) => new Date().getFullYear() - 2 + i).map((year) => (
                <option key={year} value={year.toString()}>{year}</option>
              ))}
            </select>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : requests.length === 0 ? (
              <div className="p-8 text-center">
                <Shield className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">No Requests Found</h3>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No law enforcement requests match your criteria.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full" aria-label={t("aria.adminLawEnforcement.lawEnforcementRequests")}>
                  <thead className="bg-lsc-cream dark:bg-earth-700">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Tracking #</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Agency</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Type</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Received</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                    {requests.map((request) => (
                      <tr key={request.id} className="hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20">
                        <td className="px-4 py-3 whitespace-nowrap font-medium text-lsc-dark dark:text-lsc-cream">{request.tracking_number}</td>
                        <td className="px-4 py-3 whitespace-nowrap text-lsc-dark dark:text-lsc-cream">{request.requesting_agency}</td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                            {request.request_type}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{formatDate(request.date_received)}</td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(request.workflow_status)}`}>
                            {request.workflow_status.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <button
                            onClick={() => openDetailPanel(request)}
                            className="text-lsc-rose dark:text-lsc-rose-light hover:underline text-sm flex items-center gap-1"
                          >
                            <Eye className="w-4 h-4" />
                            View Details
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-lsc-border dark:border-earth-700">
                <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Page {page} of {totalPages}</div>
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

          {showDetailPanel && selectedRequest && (
            <DetailPanel
              request={selectedRequest}
              detailLoading={detailLoading}
              detailTab={detailTab}
              checklist={checklist}
              auditLog={auditLog}
              noteText={noteText}
              onNoteChange={setNoteText}
              onClose={() => setShowDetailPanel(false)}
              onTabChange={setDetailTab}
              onChecklistToggle={handleChecklistToggle}
              onAddNote={handleAddNote}
              onWorkflowAction={(action, data) => {
                setWorkflowAction({ action, data })
                setShowWorkflowModal(true)
              }}
              getStatusColor={getStatusColor}
              formatDate={formatDate}
            />
          )}

          {showCreateModal && (
            <CreateRequestModal
              newRequest={newRequest}
              onFieldChange={(field, value) => setNewRequest({ ...newRequest, [field]: value })}
              onClose={() => setShowCreateModal(false)}
              onCreate={handleCreateRequest}
            />
          )}

          <WorkflowActionModal
            show={showWorkflowModal}
            workflowAction={workflowAction}
            noteText={noteText}
            onNoteChange={setNoteText}
            onActionChange={setWorkflowAction}
            onClose={() => {
              setShowWorkflowModal(false)
              setWorkflowAction(null)
              setNoteText("")
            }}
            onConfirm={() => {
              if (workflowAction) {
                const data = { ...workflowAction.data }
                if (noteText) data.notes = noteText
                handleWorkflowAction(workflowAction.action, data)
              }
            }}
          />
        </div>
      )}
    </SectionShell>
  )
}
