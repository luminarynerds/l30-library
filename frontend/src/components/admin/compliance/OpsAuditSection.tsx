/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useAuth } from '@/contexts/AuthContext'
import { SectionShell } from '../ai-settings/SectionShell'
import {
  getStaffAuditLogs,
  getStaffActionLabel,
  STAFF_AUDIT_ACTIONS,
  StaffAuditLog,
} from '@/api/audit-log-api'
import {
  ClipboardCheck,
  FileText,
  Search,
  Loader2,
  RefreshCw,
  Filter,
  ChevronLeft,
  ChevronRight,
  User,
  Globe,
  Clock,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

const TABS = [{ id: 'logs', label: 'Activity Log', icon: ClipboardCheck }] as const

export function OpsAuditSection({ onBack }: { onBack: () => void }) {
  const { t } = useTranslation()
  const { token } = useAuth()

  const defaultDateRange = (() => {
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - 30)
    return {
      start: start.toISOString().slice(0, 10),
      end: end.toISOString().slice(0, 10),
    }
  })()

  // Data state
  const [logs, setLogs] = useState<StaffAuditLog[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)

  // Filters
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [staffEmail, setStaffEmail] = useState('')
  const [action, setAction] = useState('')
  const [startDate, setStartDate] = useState(defaultDateRange.start)
  const [endDate, setEndDate] = useState(defaultDateRange.end)
  const [showFilters, setShowFilters] = useState(false)

  // Selected log detail
  const [selectedLog, setSelectedLog] = useState<StaffAuditLog | null>(null)

  // Ref for virtualized table
  const auditTableRef = useRef<HTMLDivElement>(null)

  // Fetch logs
  const fetchLogs = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const response = await getStaffAuditLogs(token, {
        ...(staffEmail && { admin_email: staffEmail }),
        ...(action && { action }),
        ...(startDate && { start_date: startDate }),
        ...(endDate && { end_date: endDate }),
        page,
        page_size: pageSize,
      })
      setLogs(response.logs)
      setTotal(response.total)
      setTotalPages(response.total_pages)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffAuditLog.failedToLoadAuditLogs'))
    } finally {
      setIsLoading(false)
    }
  }, [token, staffEmail, action, startDate, endDate, page, pageSize, t])

  useEffect(() => {
    if (token) fetchLogs()
  }, [token, fetchLogs])

  const handleSearch = () => {
    setPage(1)
    fetchLogs()
  }

  const clearFilters = () => {
    setStaffEmail('')
    setAction('')
    setStartDate(defaultDateRange.start)
    setEndDate(defaultDateRange.end)
    setPage(1)
  }

  // Virtualization for audit log table when more than 20 rows
  const AUDIT_ROW_HEIGHT = 56
  const shouldVirtualizeAudit = logs.length > 20

  const auditVirtualizer = useVirtualizer({
    count: logs.length,
    getScrollElement: () => auditTableRef.current,
    estimateSize: useCallback(() => AUDIT_ROW_HEIGHT, []),
    overscan: 5,
  })

  const handleSelectLog = (log: StaffAuditLog) => setSelectedLog(log)
  const handleCloseModal = () => setSelectedLog(null)

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString(getCurrentLocale(), {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  return (
    <SectionShell
      title="Operations Audit"
      description="Who did what and when. Searchable activity trail for board questions and internal review."
      tabs={[...TABS]}
      onBack={onBack}
    >
      {() => (
        <div className="space-y-4">
          {/* Header controls */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Showing {logs.length} of {total} audit log entries
            </p>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-colors ${
                  showFilters
                    ? 'bg-lsc-rose text-white'
                    : 'text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20'
                }`}
              >
                <Filter className="w-4 h-4" />
                Filters
              </button>
              <button
                onClick={fetchLogs}
                className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>
          </div>

          {/* Filters */}
          {showFilters && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Staff Member (Email)
                  </label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    <input
                      type="text"
                      value={staffEmail}
                      onChange={(e) => setStaffEmail(e.target.value)}
                      placeholder={t('staffAuditLog.searchByStaffEmail')}
                      aria-label={t('staffAuditLog.searchByStaffEmail2')}
                      className="w-full pl-10 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Action
                  </label>
                  <select
                    value={action}
                    onChange={(e) => setAction(e.target.value)}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  >
                    <option value="">All Actions</option>
                    {STAFF_AUDIT_ACTIONS.map((a) => (
                      <option key={a.value} value={a.value}>
                        {a.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Start Date
                  </label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    End Date
                  </label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-4">
                <button
                  onClick={clearFilters}
                  className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                >
                  Clear Filters
                </button>
                <button
                  onClick={handleSearch}
                  className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
                >
                  <Search className="w-4 h-4" />
                  Search
                </button>
              </div>
            </div>
          )}

          {/* Logs table */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
              </div>
            ) : logs.length === 0 ? (
              <div className="p-8 text-center">
                <FileText className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                  No Audit Logs Found
                </h3>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  No staff activity found matching your filters.
                </p>
              </div>
            ) : shouldVirtualizeAudit ? (
              <div className="overflow-x-auto">
                <div className="grid grid-cols-5 bg-lsc-cream dark:bg-earth-700 sticky top-0 z-10">
                  <div className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Time</div>
                  <div className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Staff Member</div>
                  <div className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Action</div>
                  <div className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Target User</div>
                  <div className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">IP Address</div>
                </div>
                <div
                  ref={auditTableRef}
                  className="h-[400px] overflow-auto"
                  role="table"
                  aria-label={t('aria.staffAuditLog.auditLogs')}
                >
                  <div
                    style={{
                      height: `${auditVirtualizer.getTotalSize()}px`,
                      width: '100%',
                      position: 'relative',
                    }}
                  >
                    {auditVirtualizer.getVirtualItems().map((virtualRow) => {
                      const log = logs[virtualRow.index]
                      if (!log) return null
                      return (
                        <div
                          key={log.id}
                          role="button"
                          onClick={() => handleSelectLog(log)}
                          tabIndex={0}
                          onKeyDown={(e: React.KeyboardEvent) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault()
                              handleSelectLog(log)
                            }
                          }}
                          style={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            width: '100%',
                            height: `${virtualRow.size}px`,
                            transform: `translateY(${virtualRow.start}px)`,
                          }}
                          className="grid grid-cols-5 hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 cursor-pointer transition-colors border-b border-lsc-border dark:border-earth-700"
                        >
                          <div className="px-4 py-3 whitespace-nowrap flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                            <Clock className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                            {formatDate(log.created_at)}
                          </div>
                          <div className="px-4 py-3 whitespace-nowrap flex items-center gap-2">
                            <User className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                            <span className="text-sm text-lsc-dark dark:text-lsc-cream truncate" title={log.admin_email || `Staff #${log.admin_id ?? 'Unknown'}`}>
                              {log.admin_email || `Staff #${log.admin_id ?? 'Unknown'}`}
                            </span>
                          </div>
                          <div className="px-4 py-3 whitespace-nowrap flex items-center gap-2">
                            <span className="px-2 py-1 text-xs font-medium rounded-full bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light">
                              {getStaffActionLabel(log.action)}
                            </span>
                          </div>
                          <div className="px-4 py-3 whitespace-nowrap flex items-center">
                            <span className="text-sm text-lsc-dark dark:text-lsc-cream truncate" title={log.target_user_email || (log.target_user_id ? `User #${log.target_user_id}` : 'N/A')}>
                              {log.target_user_email || (log.target_user_id ? `User #${log.target_user_id}` : 'N/A')}
                            </span>
                          </div>
                          <div className="px-4 py-3 whitespace-nowrap flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            <Globe className="w-4 h-4" />
                            {log.ip_address || 'Unknown'}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-lsc-cream dark:bg-earth-700">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Time</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Staff Member</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Action</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Target User</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">IP Address</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                    {logs.map((log) => (
                      <tr
                        key={log.id}
                        onClick={() => handleSelectLog(log)}
                        className="hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 cursor-pointer transition-colors"
                      >
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                            <Clock className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                            {formatDate(log.created_at)}
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <User className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                            <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                              {log.admin_email || `Staff #${log.admin_id ?? 'Unknown'}`}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-1 text-xs font-medium rounded-full bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light">
                              {getStaffActionLabel(log.action)}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                            {log.target_user_email || (log.target_user_id ? `User #${log.target_user_id}` : 'N/A')}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            <Globe className="w-4 h-4" />
                            {log.ip_address || 'Unknown'}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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
                    className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page === totalPages}
                    className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Log Detail Modal */}
          {selectedLog && (
            <ModalBackdrop onClose={handleCloseModal} title="Staff Activity Details">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full">
                <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                    Staff Activity Details
                  </h3>
                  <button
                    onClick={handleCloseModal}
                    className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="p-4 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Log ID</p>
                      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{selectedLog.id}</p>
                    </div>
                    <div>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Timestamp</p>
                      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                        {formatDate(selectedLog.created_at)}
                      </p>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Staff Member</p>
                    <div className="flex items-center gap-2 mt-1">
                      <User className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                      <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                        {selectedLog.admin_email || 'Unknown'}
                      </span>
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        (ID: {selectedLog.admin_id ?? 'N/A'})
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Action</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="inline-block px-3 py-1 text-sm font-medium rounded-full bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light">
                        {getStaffActionLabel(selectedLog.action)}
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Target User</p>
                    <p className="text-sm text-lsc-dark dark:text-lsc-cream mt-1">
                      {selectedLog.target_user_email || 'N/A'}
                      {selectedLog.target_user_id && (
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                          {' '}(ID: {selectedLog.target_user_id})
                        </span>
                      )}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">IP Address</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Globe className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                      <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                        {selectedLog.ip_address || 'Not recorded'}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end">
                  <button
                    onClick={handleCloseModal}
                    className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
            </ModalBackdrop>
          )}
        </div>
      )}
    </SectionShell>
  )
}
