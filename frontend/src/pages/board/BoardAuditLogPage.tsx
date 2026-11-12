/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, useMemo } from "react"
import { Link, useNavigate } from "react-router-dom"
import {
  ShieldCheck,
  Download,
  Filter,
  RefreshCw,
  Loader2,
  Search,
  X,
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  AlertCircle,
} from "lucide-react"
import toast from "react-hot-toast"

import { useAuth } from "../../contexts/AuthContext"
import { AdminShell } from "../../components/shells/AdminShell"
import { ModalBackdrop } from "@/components/ui/ModalBackdrop"
import {
  BOARD_AUDIT_ACTIONS,
  BoardAuditExportFormat,
  BoardAuditLogEntry,
  downloadBoardAuditLogExport,
  getBoardAuditActionLabel,
  getBoardAuditLogs,
} from "../../api/domains/admin/board-audit-log-api"

const PAGE_SIZE = 50

const DIRECTOR_ROLES = new Set(["director", "admin", "super_admin"])

function defaultDateRange(): { start: string; end: string } {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 30)
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  }
}

function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return ""
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

function formatDetails(details: Record<string, unknown> | null): string {
  if (!details) return ""
  try {
    const entries = Object.entries(details)
    if (entries.length === 0) return ""
    return entries
      .map(([k, v]) => {
        const text = typeof v === "string" ? v : JSON.stringify(v)
        return `${k}: ${text}`
      })
      .join(" - ")
  } catch {
    return ""
  }
}

export default function BoardAuditLogPage(): React.ReactElement {
  const { user, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  const initialRange = useMemo(() => defaultDateRange(), [])

  // Data state
  const [logs, setLogs] = useState<BoardAuditLogEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)

  // Filters
  const [actionFilter, setActionFilter] = useState("")
  const [entityType, setEntityType] = useState("")
  const [entityId, setEntityId] = useState("")
  const [userId, setUserId] = useState("")
  const [meetingId, setMeetingId] = useState("")
  const [dateFrom, setDateFrom] = useState(initialRange.start)
  const [dateTo, setDateTo] = useState(initialRange.end)
  const [showFilters, setShowFilters] = useState(false)

  // Export state
  const [isExporting, setIsExporting] = useState<BoardAuditExportFormat | null>(null)

  // Selected log detail
  const [selectedLog, setSelectedLog] = useState<BoardAuditLogEntry | null>(null)

  // Group actions for the filter <select>
  const actionGroups = useMemo(() => {
    const groups = new Map<string, typeof BOARD_AUDIT_ACTIONS[number][]>()
    for (const a of BOARD_AUDIT_ACTIONS) {
      const arr = groups.get(a.group) ?? []
      arr.push(a)
      groups.set(a.group, arr)
    }
    return Array.from(groups.entries())
  }, [])

  // Role check
  useEffect(() => {
    if (authLoading) return
    if (!user || !DIRECTOR_ROLES.has(user.role)) {
      toast.error("Director or admin access required")
      navigate("/staff")
    }
  }, [authLoading, user, navigate])

  const buildFilters = useCallback(() => {
    return {
      action: actionFilter || undefined,
      entity_type: entityType.trim() || undefined,
      entity_id: entityId.trim() ? Number(entityId.trim()) : undefined,
      user_id: userId.trim() ? Number(userId.trim()) : undefined,
      meeting_id: meetingId.trim() ? Number(meetingId.trim()) : undefined,
      date_from: dateFrom ? `${dateFrom}T00:00:00` : undefined,
      date_to: dateTo ? `${dateTo}T23:59:59` : undefined,
    }
  }, [actionFilter, entityType, entityId, userId, meetingId, dateFrom, dateTo])

  // Fetch logs
  const fetchLogs = useCallback(async () => {
    if (!user || !DIRECTOR_ROLES.has(user.role)) return
    setIsLoading(true)
    setError(null)
    try {
      const skip = (page - 1) * PAGE_SIZE
      // Request one extra row to detect whether there is a next page.
      const data = await getBoardAuditLogs({
        ...buildFilters(),
        skip,
        limit: PAGE_SIZE + 1,
      })
      setHasMore(data.length > PAGE_SIZE)
      setLogs(data.slice(0, PAGE_SIZE))
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load audit logs"
      setError(msg)
      setLogs([])
      setHasMore(false)
    } finally {
      setIsLoading(false)
    }
  }, [user, page, buildFilters])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  const applyFilters = () => {
    setPage(1)
    fetchLogs()
  }

  const clearFilters = () => {
    setActionFilter("")
    setEntityType("")
    setEntityId("")
    setUserId("")
    setMeetingId("")
    setDateFrom(initialRange.start)
    setDateTo(initialRange.end)
    setPage(1)
  }

  const handleExport = async (format: BoardAuditExportFormat) => {
    setIsExporting(format)
    try {
      await downloadBoardAuditLogExport(format, buildFilters())
      toast.success(`Exported as ${format.toUpperCase()}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Export failed"
      toast.error(msg)
    } finally {
      setIsExporting(null)
    }
  }

  const headerActions = (
    <>
      <button
        type="button"
        onClick={() => setShowFilters((v) => !v)}
        className="inline-flex items-center gap-2 rounded-lg border border-lsc-dark/20 dark:border-lsc-cream/20 px-3 py-1.5 text-sm hover:bg-lsc-dark/5 dark:hover:bg-lsc-cream/5"
      >
        <Filter className="w-4 h-4" />
        Filters
      </button>
      <button
        type="button"
        onClick={() => fetchLogs()}
        disabled={isLoading}
        className="inline-flex items-center gap-2 rounded-lg border border-lsc-dark/20 dark:border-lsc-cream/20 px-3 py-1.5 text-sm hover:bg-lsc-dark/5 dark:hover:bg-lsc-cream/5 disabled:opacity-50"
      >
        <RefreshCw className={`w-4 h-4 ${isLoading ? "motion-safe:animate-spin" : ""}`} />
        Refresh
      </button>
      <button
        type="button"
        onClick={() => handleExport("csv")}
        disabled={isExporting !== null}
        className="inline-flex items-center gap-2 rounded-lg bg-lsc-rose px-3 py-1.5 text-sm text-white hover:bg-lsc-rose/90 disabled:opacity-50"
      >
        {isExporting === "csv" ? (
          <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
        ) : (
          <Download className="w-4 h-4" />
        )}
        Export CSV
      </button>
      <button
        type="button"
        onClick={() => handleExport("json")}
        disabled={isExporting !== null}
        className="inline-flex items-center gap-2 rounded-lg border border-lsc-rose text-lsc-rose px-3 py-1.5 text-sm hover:bg-lsc-rose/10 disabled:opacity-50"
      >
        {isExporting === "json" ? (
          <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
        ) : (
          <Download className="w-4 h-4" />
        )}
        Export JSON
      </button>
    </>
  )

  return (
    <AdminShell
      title="Board Audit Log"
      subtitle="Tamper-resistant governance audit trail. Append-only at the database level. Director and admin access."
      icon={<ShieldCheck className="w-7 h-7 text-lsc-rose" />}
      actions={headerActions}
    >
      <div className="mb-2">
        <Link
          to="/staff/admin/board"
          className="inline-flex items-center gap-2 text-sm text-lsc-rose hover:text-lsc-rose/80"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Board Management
        </Link>
      </div>

      {showFilters && (
        <div className="rounded-lg border border-lsc-dark/15 dark:border-lsc-cream/15 bg-white/60 dark:bg-earth-800/60 p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Action</span>
              <select
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                className="rounded border border-lsc-dark/20 dark:border-lsc-cream/20 bg-transparent px-2 py-1.5"
              >
                <option value="">All actions</option>
                {actionGroups.map(([group, actions]) => (
                  <optgroup key={group} label={group}>
                    {actions.map((a) => (
                      <option key={a.value} value={a.value}>
                        {a.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Entity type</span>
              <input
                type="text"
                value={entityType}
                onChange={(e) => setEntityType(e.target.value)}
                placeholder="e.g. BoardMeeting"
                className="rounded border border-lsc-dark/20 dark:border-lsc-cream/20 bg-transparent px-2 py-1.5"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Entity ID</span>
              <input
                type="number"
                value={entityId}
                onChange={(e) => setEntityId(e.target.value)}
                className="rounded border border-lsc-dark/20 dark:border-lsc-cream/20 bg-transparent px-2 py-1.5"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">User ID</span>
              <input
                type="number"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                className="rounded border border-lsc-dark/20 dark:border-lsc-cream/20 bg-transparent px-2 py-1.5"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Meeting ID</span>
              <input
                type="number"
                value={meetingId}
                onChange={(e) => setMeetingId(e.target.value)}
                className="rounded border border-lsc-dark/20 dark:border-lsc-cream/20 bg-transparent px-2 py-1.5"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">From</span>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="rounded border border-lsc-dark/20 dark:border-lsc-cream/20 bg-transparent px-2 py-1.5"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">To</span>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="rounded border border-lsc-dark/20 dark:border-lsc-cream/20 bg-transparent px-2 py-1.5"
              />
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={clearFilters}
              className="inline-flex items-center gap-2 rounded-lg border border-lsc-dark/20 dark:border-lsc-cream/20 px-3 py-1.5 text-sm hover:bg-lsc-dark/5"
            >
              <X className="w-4 h-4" />
              Clear
            </button>
            <button
              type="button"
              onClick={applyFilters}
              className="inline-flex items-center gap-2 rounded-lg bg-lsc-rose px-3 py-1.5 text-sm text-white hover:bg-lsc-rose/90"
            >
              <Search className="w-4 h-4" />
              Apply
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 rounded-lg border border-status-danger-300 bg-status-danger-50 dark:bg-status-danger-900/20 p-3 text-status-danger-700 dark:text-status-danger-300">
          <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
          <div className="text-sm">{error}</div>
        </div>
      )}

      <div className="rounded-lg border border-lsc-dark/15 dark:border-lsc-cream/15 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-lsc-dark/5 dark:bg-earth-900/40 text-left">
              <tr>
                <th className="px-3 py-2 font-medium">When</th>
                <th className="px-3 py-2 font-medium">Action</th>
                <th className="px-3 py-2 font-medium">Entity</th>
                <th className="px-3 py-2 font-medium">User</th>
                <th className="px-3 py-2 font-medium">Meeting</th>
                <th className="px-3 py-2 font-medium">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-lsc-dark/10 dark:divide-lsc-cream/10">
              {isLoading && (
                <tr>
                  <td colSpan={6} className="px-3 py-12 text-center">
                    <Loader2 className="w-6 h-6 motion-safe:animate-spin mx-auto text-lsc-rose" />
                  </td>
                </tr>
              )}
              {!isLoading && logs.length === 0 && !error && (
                <tr>
                  <td colSpan={6} className="px-3 py-12 text-center text-lsc-dark/60 dark:text-lsc-cream/60">
                    No audit log entries match these filters.
                  </td>
                </tr>
              )}
              {!isLoading &&
                logs.map((log) => (
                  <tr
                    key={log.id}
                    className="hover:bg-lsc-dark/5 dark:hover:bg-earth-900/40 cursor-pointer"
                    onClick={() => setSelectedLog(log)}
                  >
                    <td className="px-3 py-2 whitespace-nowrap text-lsc-dark/80 dark:text-lsc-cream/80">
                      {formatTimestamp(log.created_at)}
                    </td>
                    <td className="px-3 py-2">
                      <span className="inline-block rounded bg-lsc-rose/10 text-lsc-rose px-2 py-0.5 text-xs">
                        {getBoardAuditActionLabel(log.action)}
                      </span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {log.entity_type}
                      <span className="text-lsc-dark/50 dark:text-lsc-cream/50"> #{log.entity_id}</span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-lsc-dark/80 dark:text-lsc-cream/80">
                      {log.user_id != null ? `#${log.user_id}` : "system"}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-lsc-dark/80 dark:text-lsc-cream/80">
                      {log.meeting_id != null ? `#${log.meeting_id}` : ""}
                    </td>
                    <td className="px-3 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 max-w-md truncate">
                      {formatDetails(log.details)}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between border-t border-lsc-dark/10 dark:border-lsc-cream/10 px-3 py-2 text-sm">
          <span className="text-lsc-dark/60 dark:text-lsc-cream/60">
            Page {page}
            {logs.length > 0 ? ` - ${logs.length} entr${logs.length === 1 ? "y" : "ies"}` : ""}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || isLoading}
              className="inline-flex items-center gap-1 rounded border border-lsc-dark/20 dark:border-lsc-cream/20 px-2 py-1 disabled:opacity-50"
            >
              <ChevronLeft className="w-4 h-4" />
              Prev
            </button>
            <button
              type="button"
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasMore || isLoading}
              className="inline-flex items-center gap-1 rounded border border-lsc-dark/20 dark:border-lsc-cream/20 px-2 py-1 disabled:opacity-50"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {selectedLog && (
        <ModalBackdrop onClose={() => setSelectedLog(null)}>
          <div className="bg-white dark:bg-earth-900 rounded-lg shadow-lg max-w-2xl w-full mx-4 p-6 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                  {getBoardAuditActionLabel(selectedLog.action)}
                </h2>
                <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
                  {formatTimestamp(selectedLog.created_at)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                className="text-lsc-dark/60 hover:text-lsc-dark dark:text-lsc-cream/60 dark:hover:text-lsc-cream"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <dl className="grid grid-cols-3 gap-2 text-sm">
              <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">ID</dt>
              <dd className="col-span-2">{selectedLog.id}</dd>
              <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">Action code</dt>
              <dd className="col-span-2 font-mono text-xs">{selectedLog.action}</dd>
              <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">Entity</dt>
              <dd className="col-span-2">
                {selectedLog.entity_type} #{selectedLog.entity_id}
              </dd>
              <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">User ID</dt>
              <dd className="col-span-2">{selectedLog.user_id ?? "system"}</dd>
              <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">Meeting ID</dt>
              <dd className="col-span-2">{selectedLog.meeting_id ?? "-"}</dd>
              <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">IP address</dt>
              <dd className="col-span-2 font-mono text-xs">{selectedLog.ip_address ?? "-"}</dd>
              <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">Notes</dt>
              <dd className="col-span-2 whitespace-pre-wrap">{selectedLog.notes ?? "-"}</dd>
            </dl>
            {selectedLog.details && Object.keys(selectedLog.details).length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Details</h3>
                <pre className="bg-lsc-dark/5 dark:bg-earth-800 rounded p-3 text-xs overflow-auto max-h-60">
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </ModalBackdrop>
      )}
    </AdminShell>
  )
}
