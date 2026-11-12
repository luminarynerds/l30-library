/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import { fetchApi } from '@/api/fetchApi';
import {
  RotateCcw,
  RefreshCw,
  Loader2,
  AlertTriangle,
  Clock,
  User,
  ChevronLeft,
  ChevronRight,
  X,
  History,
  Shield,
} from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation, getCurrentLocale } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

// Backend wire shapes (snake_case). The page previously consumed an approval
// workflow API (/audit-reversal/entries|requests|request|approve|reject) that
// was never implemented. The real backend is a direct-revert model:
//   GET  /admin/audit-logs?skip&limit            -> {total, items:[AuditEntry]}
//   GET  /admin/audit/reversible-actions         -> {reversible[], non_reversible[]}
//   GET  /admin/audit/{id}/can-revert            -> ReversibilityCheck
//   POST /admin/audit/{id}/revert                -> ReversalResult
// Admin / super-admin only (backend require_admin_for_reversal).
interface AuditEntry {
  id: number
  action: string
  admin_id?: number | null
  target_user_id?: number | null
  details?: Record<string, unknown> | null
  ip_address?: string | null
  created_at: string
}

interface ReversibilityCheck {
  audit_log_id: number
  is_reversible: boolean
  action: string
  reason: string
  details?: Record<string, unknown> | null
  warnings: string[]
}

export default function StaffAuditReversalPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([])
  const [reversibleActions, setReversibleActions] = useState<Set<string>>(new Set())
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showReversalModal, setShowReversalModal] = useState(false)
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null)
  const [check, setCheck] = useState<ReversibilityCheck | null>(null)
  const [checkLoading, setCheckLoading] = useState(false)
  const [reverting, setReverting] = useState(false)

  const pageSize = 20
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const isAdmin = !!user && ["admin", "super_admin"].includes(user.role)

  useEffect(() => {
    if (!authLoading && !isAdmin) {
      toast.error(t('toast.adminAPIStatus.adminAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAdmin, navigate, t])

  // Action types the backend can reverse (documentation endpoint). Used to
  // enable the Revert button only where a reversal is even possible.
  const fetchReversibleActions = useCallback(async () => {
    if (!token) return
    try {
      const data = await fetchApi(`/admin/audit/reversible-actions`)
      setReversibleActions(new Set<string>(data?.reversible ?? []))
    } catch {
      // Non-fatal: without this the buttons fall back to letting can-revert decide.
    }
  }, [token])

  const fetchAuditEntries = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * pageSize),
        limit: String(pageSize),
      })
      const data = await fetchApi(`/admin/audit-logs?${params}`)
      setAuditEntries(Array.isArray(data?.items) ? data.items : [])
      setTotal(data?.total || 0)
    } catch {
      toast.error(t('staffAuditReversal.failedToLoadAuditEntries'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, page])

  useEffect(() => {
    if (token && isAuthenticated) {
      fetchReversibleActions()
      fetchAuditEntries()
    }
  }, [token, isAuthenticated, fetchReversibleActions, fetchAuditEntries])

  const isReverted = (entry: AuditEntry) =>
    !!(entry.details && (entry.details as Record<string, unknown>).reverted)

  const canAttemptRevert = (entry: AuditEntry) =>
    reversibleActions.has(entry.action) && !isReverted(entry)

  const openRevertModal = async (entry: AuditEntry) => {
    setSelectedEntry(entry)
    setCheck(null)
    setShowReversalModal(true)
    if (!token) return
    setCheckLoading(true)
    try {
      const data = await fetchApi(`/admin/audit/${entry.id}/can-revert`)
      setCheck(data as ReversibilityCheck)
    } catch {
      toast.error(t('staffAuditReversal.failedToLoadAuditEntries'))
    } finally {
      setCheckLoading(false)
    }
  }

  const handleRevert = async () => {
    if (!token || !selectedEntry) return
    setReverting(true)
    try {
      const data = await fetchApi(`/admin/audit/${selectedEntry.id}/revert`, {
        method: "POST",
      })
      const warnings: string[] = data?.warnings ?? []
      toast.success(
        warnings.length
          ? `Action reverted with ${warnings.length} warning(s).`
          : "Action reverted.",
      )
      setShowReversalModal(false)
      setSelectedEntry(null)
      setCheck(null)
      fetchAuditEntries()
    } catch {
      toast.error("Failed to revert this action.")
    } finally {
      setReverting(false)
    }
  }

  const getActionTypeColor = (action: string) => {
    const a = action.toLowerCase()
    if (a.includes("delete") || a.includes("remove") || a.includes("lock"))
      return "text-status-danger-600 dark:text-status-danger-400 bg-status-danger-100 dark:bg-status-danger-900/30"
    if (a.includes("create") || a.includes("add") || a.includes("grant"))
      return "text-status-success-600 dark:text-status-success-400 bg-status-success-100 dark:bg-status-success-900/30"
    if (a.includes("update") || a.includes("change") || a.includes("edit"))
      return "text-lsc-rose dark:text-lsc-rose-light bg-earth-100 dark:bg-earth-800/30"
    return "text-lsc-dark/70 dark:text-lsc-cream/70 bg-earth-100 dark:bg-earth-700"
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString(getCurrentLocale(), {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!isAdmin) {
    return <></>
  }

  return (
    <AdminShell title="Audit Reversal Operations">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Audit Reversal Operations
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Review recent audit log actions and revert reversible ones.
              </p>
            </div>
            <button
              onClick={fetchAuditEntries}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>

          {/* Audit Entries */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : auditEntries.length === 0 ? (
              <div className="p-8 text-center">
                <History className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffAuditReversal.noReversibleAuditEntriesFound')}</p>
              </div>
            ) : (
              <div className="divide-y divide-lsc-border dark:divide-earth-700">
                {auditEntries.map((entry) => (
                  <div key={entry.id} className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getActionTypeColor(entry.action)}`}>
                            {entry.action}
                          </span>
                          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                            #{entry.id}
                          </span>
                          {isReverted(entry) && (
                            <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-400">
                              Reverted
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          {entry.admin_id != null && (
                            <span className="flex items-center gap-1">
                              <User className="w-3 h-3" />
                              admin #{entry.admin_id}
                            </span>
                          )}
                          {entry.target_user_id != null && (
                            <span>target #{entry.target_user_id}</span>
                          )}
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatDate(entry.created_at)}
                          </span>
                          {entry.ip_address && <span>IP: {entry.ip_address}</span>}
                        </div>
                      </div>
                      {canAttemptRevert(entry) && (
                        <button
                          onClick={() => openRevertModal(entry)}
                          className="flex items-center gap-2 px-3 py-1.5 text-sm text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg"
                        >
                          <RotateCcw className="w-4 h-4" />
                          Revert
                        </button>
                      )}
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
                    className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 disabled:opacity-50"
                    aria-label="Previous page"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page === totalPages}
                    className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 disabled:opacity-50"
                    aria-label="Next page"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
              </div>
            )}
          </div>

      {/* Revert Confirmation Modal */}
      {showReversalModal && selectedEntry && (
        <ModalBackdrop onClose={() => setShowReversalModal(false)} title="Revert Action">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
            <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <Shield className="w-5 h-5" />
                Revert Action
              </h3>
              <button onClick={() => setShowReversalModal(false)} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70" aria-label={t('aria.authModals.close')}>
                <X className="w-5 h-5" aria-hidden="true" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Reverting <span className="font-medium text-lsc-dark dark:text-lsc-cream">{selectedEntry.action}</span> (audit log #{selectedEntry.id}).
              </p>

              {checkLoading ? (
                <div className="flex items-center justify-center py-6">
                  <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
                </div>
              ) : check ? (
                <>
                  {check.reason && (
                    <p className="text-sm text-lsc-dark dark:text-lsc-cream bg-lsc-cream/50 dark:bg-earth-700 p-2 rounded">
                      {check.reason}
                    </p>
                  )}
                  {check.warnings.length > 0 && (
                    <div className="p-3 bg-status-warning-50 dark:bg-status-warning-900/30 border border-status-warning-200 dark:border-status-warning-800 rounded-lg">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="w-5 h-5 text-status-warning-500 mt-0.5" />
                        <ul className="text-sm text-status-warning-700 dark:text-status-warning-400 list-disc pl-4 space-y-1">
                          {check.warnings.map((w, i) => (
                            <li key={i}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                  {!check.is_reversible && (
                    <p className="text-sm text-status-danger-600 dark:text-status-danger-400">
                      This action cannot be reverted.
                    </p>
                  )}
                </>
              ) : null}
            </div>
            <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
              <button
                onClick={() => setShowReversalModal(false)}
                className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70"
              >
                Cancel
              </button>
              <button
                onClick={handleRevert}
                disabled={reverting || checkLoading || !check?.is_reversible}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
              >
                {reverting ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <RotateCcw className="w-4 h-4" />}
                Confirm Revert
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </AdminShell>
  )
}
