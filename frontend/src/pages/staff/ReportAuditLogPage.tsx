/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ClipboardList, ChevronLeft, ChevronRight, ArrowUp, ArrowDown, ArrowUpDown, Zap, Clock, Download } from 'lucide-react'
import { AdminShell } from '@/components/shells/AdminShell'
import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import { getCurrentLocale } from '@/i18n'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuditLogEntry {
  id: number
  report_type: string
  format: string
  date_range_start: string | null
  date_range_end: string | null
  generated_by_id: number | null
  generated_by_email: string | null
  generated_at: string
  duration_ms: number | null
  record_count: number | null
  cache_hit: boolean
}

interface AuditLogResponse {
  items: AuditLogEntry[]
  total: number
  limit: number
  offset: number
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const REPORT_TYPE_LABELS: Record<string, string> = {
  circulation: 'Circulation',
  financial: 'Financial',
  patron_activity: 'Patron Activity',
  collection: 'Collection',
  compliance: 'Compliance',
  community_outcomes: 'Community Activity',
}

const ALL_REPORT_TYPES = Object.keys(REPORT_TYPE_LABELS)
const PAGE_SIZE = 25

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

type SortBy = 'generated_at' | 'duration_ms' | 'record_count'
type SortOrder = 'asc' | 'desc'

async function fetchAuditLog(params: {
  report_type?: string
  start_date?: string
  end_date?: string
  sort_by: SortBy
  sort_order: SortOrder
  limit: number
  offset: number
}): Promise<AuditLogResponse> {
  const token = getAccessToken()
  const sp = new URLSearchParams()
  sp.set('limit', String(params.limit))
  sp.set('offset', String(params.offset))
  sp.set('sort_by', params.sort_by)
  sp.set('sort_order', params.sort_order)
  if (params.report_type) sp.set('report_type', params.report_type)
  if (params.start_date) sp.set('start_date', params.start_date)
  if (params.end_date) sp.set('end_date', params.end_date)
  return fetchApi<AuditLogResponse>(`/unified-reports/audit-log?${sp}`, {
    ...(token ? { token } : {}),
  })
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(getCurrentLocale(), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatDateRange(start: string | null, end: string | null): string {
  if (!start && !end) return '--'
  const fmt = (s: string) =>
    new Date(s).toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' })
  if (start && end) return `${fmt(start)} - ${fmt(end)}`
  if (start) return `${fmt(start)} - now`
  return `up to ${fmt(end!)}`
}

function formatDuration(ms: number | null): string {
  if (ms === null) return '--'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ReportAuditLogPage() {
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [offset, setOffset] = useState(0)
  const [sortBy, setSortBy] = useState<SortBy>('generated_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['report-audit-log', typeFilter, startDate, endDate, sortBy, sortOrder, offset],
    queryFn: () =>
      fetchAuditLog({
        report_type: typeFilter || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: PAGE_SIZE,
        offset,
      }),
    placeholderData: keepPreviousData,
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  const toggleSort = (col: SortBy) => {
    if (sortBy === col) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(col)
      setSortOrder('desc')
    }
    setOffset(0)
  }

  const ariaSortFor = (col: SortBy): 'ascending' | 'descending' | 'none' =>
    sortBy === col ? (sortOrder === 'asc' ? 'ascending' : 'descending') : 'none'

  const renderSortHeader = (col: SortBy, label: string, align: 'left' | 'right' = 'left') => (
    <th
      scope="col"
      aria-sort={ariaSortFor(col)}
      className={`px-4 py-3 font-medium text-earth-600 dark:text-earth-300 ${align === 'right' ? 'text-right' : ''}`}
    >
      <button
        type="button"
        onClick={() => toggleSort(col)}
        className={`inline-flex items-center gap-1 hover:text-lsc-rose focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded ${align === 'right' ? 'flex-row-reverse' : ''}`}
      >
        {label}
        {sortBy === col ? (
          sortOrder === 'asc'
            ? <ArrowUp className="h-3 w-3" aria-hidden="true" />
            : <ArrowDown className="h-3 w-3" aria-hidden="true" />
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-40" aria-hidden="true" />
        )}
      </button>
    </th>
  )

  const handleExport = async () => {
    setExporting(true)
    setExportError(null)
    try {
      const token = getAccessToken()
      const sp = new URLSearchParams()
      sp.set('sort_by', sortBy)
      sp.set('sort_order', sortOrder)
      if (typeFilter) sp.set('report_type', typeFilter)
      if (startDate) sp.set('start_date', startDate)
      if (endDate) sp.set('end_date', endDate)
      // eslint-disable-next-line no-restricted-syntax -- binary CSV download needs raw fetch + blob, not fetchApi
      const res = await fetch(`${API_BASE}/unified-reports/audit-log/export?${sp}`, {
        credentials: 'include',
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      })
      if (!res.ok) throw new Error(`Export failed: ${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'report-audit-log.csv'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      setExportError('Could not download the CSV. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  const clearFilters = () => {
    setTypeFilter('')
    setStartDate('')
    setEndDate('')
    setOffset(0)
  }

  return (
    <AdminShell
      title="Report Audit Log"
      subtitle="Track who generated which reports and when"
      icon={<ClipboardList className="h-6 w-6" />}
      loading={isLoading}
      error={isError ? (error instanceof Error ? error.message : 'Failed to load audit log') : null}
      actions={
        <>
          <button
            type="button"
            onClick={handleExport}
            disabled={exporting || !data || data.total === 0}
            className="inline-flex items-center gap-1 text-sm text-lsc-rose hover:text-lsc-rose/80 underline disabled:opacity-40 min-h-[44px]"
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            {exporting ? 'Preparing...' : 'Download CSV'}
          </button>
          <Link
            to="/staff/audit-logs"
            className="text-sm text-lsc-rose hover:text-lsc-rose/80 underline"
          >
            Staff Activity Audit
          </Link>
          <Link
            to="/staff/reports/unified"
            className="text-sm text-lsc-rose hover:text-lsc-rose/80 underline"
          >
            Back to Reports
          </Link>
        </>
      }
    >
      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs font-medium text-earth-600 dark:text-earth-400 mb-1">
            Report Type
          </label>
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setOffset(0) }}
            className="rounded-lg border border-lsc-border dark:border-earth-700 bg-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream min-h-[44px]"
          >
            <option value="">All types</option>
            {ALL_REPORT_TYPES.map((t) => (
              <option key={t} value={t}>{REPORT_TYPE_LABELS[t]}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-earth-600 dark:text-earth-400 mb-1">
            From
          </label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => { setStartDate(e.target.value); setOffset(0) }}
            className="rounded-lg border border-lsc-border dark:border-earth-700 bg-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream min-h-[44px]"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-earth-600 dark:text-earth-400 mb-1">
            To
          </label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => { setEndDate(e.target.value); setOffset(0) }}
            className="rounded-lg border border-lsc-border dark:border-earth-700 bg-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream min-h-[44px]"
          />
        </div>

        {(typeFilter || startDate || endDate) && (
          <button
            onClick={clearFilters}
            className="text-sm text-earth-600 dark:text-earth-400 hover:text-lsc-rose underline min-h-[44px]"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Result count, announced to assistive tech */}
      <p role="status" aria-live="polite" className="mb-3 text-sm text-earth-600 dark:text-earth-400">
        {data ? `Showing ${data.items.length} of ${data.total} report ${data.total === 1 ? 'entry' : 'entries'}` : ''}
      </p>
      {exportError && (
        <p role="alert" className="mb-3 text-sm text-status-danger-600 dark:text-status-danger-400">
          {exportError}
        </p>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-lsc-border dark:border-earth-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-earth-50 dark:bg-earth-800/50 text-left">
              <th scope="col" className="px-4 py-3 font-medium text-earth-600 dark:text-earth-300">Report Type</th>
              <th scope="col" className="px-4 py-3 font-medium text-earth-600 dark:text-earth-300">Format</th>
              <th scope="col" className="px-4 py-3 font-medium text-earth-600 dark:text-earth-300">Date Range</th>
              <th scope="col" className="px-4 py-3 font-medium text-earth-600 dark:text-earth-300">Generated By</th>
              {renderSortHeader('generated_at', 'Generated At')}
              {renderSortHeader('duration_ms', 'Duration', 'right')}
              {renderSortHeader('record_count', 'Records', 'right')}
              <th scope="col" className="px-4 py-3 font-medium text-earth-600 dark:text-earth-300 text-center">Cache</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-earth-600 dark:text-earth-500">
                  No report generation logs found.
                </td>
              </tr>
            )}
            {data?.items.map((entry) => (
              <tr
                key={entry.id}
                className="hover:bg-earth-50 dark:hover:bg-earth-800/30 transition-colors"
              >
                <td className="px-4 py-3 text-lsc-dark dark:text-lsc-cream font-medium">
                  {REPORT_TYPE_LABELS[entry.report_type] || entry.report_type}
                </td>
                <td className="px-4 py-3">
                  <span className="uppercase text-xs font-mono bg-earth-100 dark:bg-earth-800 text-earth-600 dark:text-earth-300 px-1.5 py-0.5 rounded">
                    {entry.format}
                  </span>
                </td>
                <td className="px-4 py-3 text-earth-600 dark:text-earth-400">
                  {formatDateRange(entry.date_range_start, entry.date_range_end)}
                </td>
                <td className="px-4 py-3 text-earth-600 dark:text-earth-400">
                  {entry.generated_by_email || '--'}
                </td>
                <td className="px-4 py-3 text-earth-600 dark:text-earth-400">
                  {formatDate(entry.generated_at)}
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="inline-flex items-center gap-1 text-earth-600 dark:text-earth-400">
                    <Clock className="h-3 w-3" />
                    {formatDuration(entry.duration_ms)}
                  </span>
                </td>
                <td className="px-4 py-3 text-right text-earth-600 dark:text-earth-400">
                  {entry.record_count !== null ? entry.record_count.toLocaleString() : '--'}
                </td>
                <td className="px-4 py-3 text-center">
                  {entry.cache_hit ? (
                    <span className="inline-flex items-center gap-1 text-status-success-600 dark:text-status-success-400 text-xs">
                      <Zap className="h-3 w-3" /> Hit
                    </span>
                  ) : (
                    <span className="text-earth-600 dark:text-earth-400 text-xs">Fresh</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-earth-600 dark:text-earth-400">
            Showing {offset + 1}--{Math.min(offset + PAGE_SIZE, data?.total || 0)} of {data?.total || 0}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0}
              className="inline-flex items-center gap-1 rounded-lg border border-lsc-border dark:border-earth-700 px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-earth-50 dark:hover:bg-earth-800 min-h-[44px]"
            >
              <ChevronLeft className="h-4 w-4" /> Prev
            </button>
            <span className="text-sm text-earth-600 dark:text-earth-400">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={currentPage >= totalPages}
              className="inline-flex items-center gap-1 rounded-lg border border-lsc-border dark:border-earth-700 px-3 py-1.5 text-sm disabled:opacity-40 hover:bg-earth-50 dark:hover:bg-earth-800 min-h-[44px]"
            >
              Next <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </AdminShell>
  )
}
