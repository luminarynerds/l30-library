/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CalendarClock, CheckCircle2, Inbox, AlertCircle, Search } from 'lucide-react'
import * as Sentry from "@/lib/sentry-lazy"
import toast from 'react-hot-toast'
import { AdminShell } from '../components/shells'
import {
  listSerialIssues,
  checkinSerialIssues,
  createSerialClaim,
  type SerialIssue,
  type SerialIssueStatus,
} from '../api/domains/admin/serials-api'

const PER_PAGE = 50

const STATUS_LABELS: Record<SerialIssueStatus, string> = {
  expected: 'Expected',
  received: 'Received',
  late: 'Late',
  claimed: 'Claimed',
  missing: 'Missing',
  not_published: 'Not published',
}

const STATUS_COLORS: Record<SerialIssueStatus, string> = {
  expected: 'bg-status-info-100 dark:bg-status-info-900/30 text-status-info-800 dark:text-status-info-200',
  received: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-200',
  late: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-200',
  claimed: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-200',
  missing: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-200',
  not_published: 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70',
}

export default function SerialIssuesPage(): React.ReactElement {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialStatus = (searchParams.get('status') as SerialIssueStatus | null) || null

  const [issues, setIssues] = useState<SerialIssue[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<SerialIssueStatus | 'all'>(initialStatus ?? 'all')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [refreshKey, setRefreshKey] = useState(0)
  const [actionLoading, setActionLoading] = useState(false)

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    listSerialIssues({
      page,
      per_page: PER_PAGE,
      ...(statusFilter !== 'all' ? { status: statusFilter } : {}),
    })
      .then((res) => {
        if (cancelled) return
        let items = res.items
        if (search) {
          const q = search.toLowerCase()
          items = items.filter(
            (i) =>
              (i.serial_title_name || '').toLowerCase().includes(q) ||
              (i.designation || '').toLowerCase().includes(q) ||
              (i.barcode || '').toLowerCase().includes(q),
          )
        }
        setIssues(items)
        setTotal(res.total)
      })
      .catch((e: unknown) => {
        Sentry.captureException(e instanceof Error ? e : new Error(String(e)))
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load issues')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [page, statusFilter, refreshKey, search])

  const toggleAll = () => {
    if (selected.size === issues.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(issues.map((i) => i.id)))
    }
  }

  const toggle = (id: number) => {
    setSelected((s) => {
      const next = new Set(s)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleCheckin = async () => {
    if (selected.size === 0) return
    setActionLoading(true)
    try {
      const result = await checkinSerialIssues({ issue_ids: Array.from(selected) })
      toast.success(`Checked in ${result.checked_in} issue${result.checked_in === 1 ? '' : 's'}`)
      setSelected(new Set())
      refresh()
    } catch (e: unknown) {
      Sentry.captureException(e instanceof Error ? e : new Error(String(e)))
      toast.error(e instanceof Error ? e.message : 'Check-in failed')
    } finally {
      setActionLoading(false)
    }
  }

  const handleClaim = async () => {
    if (selected.size === 0) return
    if (selected.size > 1) {
      toast.error('Claim one issue at a time for now')
      return
    }
    const issueId = Array.from(selected)[0]
    if (!issueId) return
    setActionLoading(true)
    try {
      await createSerialClaim(issueId, { claim_type: 'not_received' })
      toast.success('Claim filed with vendor')
      setSelected(new Set())
      refresh()
    } catch (e: unknown) {
      Sentry.captureException(e instanceof Error ? e : new Error(String(e)))
      toast.error(e instanceof Error ? e.message : 'Claim failed')
    } finally {
      setActionLoading(false)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  return (
    <AdminShell
      title="Serial Issues"
      subtitle={`${total} issue${total === 1 ? '' : 's'}`}
      icon={<CalendarClock className="w-7 h-7 text-lsc-rose" />}
      error={error}
    >
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter by title, designation, or barcode"
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => {
            const v = e.target.value as SerialIssueStatus | 'all'
            setStatusFilter(v)
            setPage(1)
            if (v === 'all') {
              searchParams.delete('status')
            } else {
              searchParams.set('status', v)
            }
            setSearchParams(searchParams, { replace: true })
          }}
          className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        >
          <option value="all">All statuses</option>
          {(Object.keys(STATUS_LABELS) as SerialIssueStatus[]).map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
      </div>

      {selected.size > 0 && (
        <div className="mb-4 p-3 rounded-lg border border-lsc-rose/30 bg-lsc-rose/5 dark:bg-lsc-rose/10 flex items-center justify-between flex-wrap gap-3">
          <span className="text-sm text-lsc-dark dark:text-lsc-cream">
            <strong>{selected.size}</strong> issue{selected.size === 1 ? '' : 's'} selected
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleCheckin}
              disabled={actionLoading}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-status-success-600 text-white hover:bg-status-success-700 disabled:opacity-50 text-sm font-medium"
            >
              <CheckCircle2 className="w-4 h-4" />
              Check in
            </button>
            <button
              onClick={handleClaim}
              disabled={actionLoading || selected.size > 1}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-status-warning-600 text-white hover:bg-status-warning-700 disabled:opacity-50 text-sm font-medium"
              title={selected.size > 1 ? 'Select one issue to claim' : 'File a claim with the vendor'}
            >
              <Inbox className="w-4 h-4" />
              File claim
            </button>
            <button
              onClick={() => setSelected(new Set())}
              className="px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-600 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-lsc-cream/30 dark:bg-earth-700/30">
              <tr className="border-b border-lsc-border dark:border-earth-700">
                <th className="px-3 py-3 w-10">
                  <input
                    type="checkbox"
                    checked={issues.length > 0 && selected.size === issues.length}
                    onChange={toggleAll}
                    className="w-4 h-4"
                    aria-label="Select all"
                  />
                </th>
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Title</th>
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Designation</th>
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Expected</th>
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Received</th>
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Status</th>
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Branch</th>
                <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-lsc-dark/70 dark:text-lsc-cream/60">
                    Loading...
                  </td>
                </tr>
              ) : issues.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-lsc-dark/70 dark:text-lsc-cream/60">
                    <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    No issues match.
                  </td>
                </tr>
              ) : (
                issues.map((issue) => (
                  <tr
                    key={issue.id}
                    className={`border-b border-lsc-border/50 dark:border-earth-700/50 hover:bg-lsc-cream/20 dark:hover:bg-earth-700/20 ${
                      selected.has(issue.id) ? 'bg-lsc-rose/5 dark:bg-lsc-rose/10' : ''
                    }`}
                  >
                    <td className="px-3 py-3">
                      <input
                        type="checkbox"
                        checked={selected.has(issue.id)}
                        onChange={() => toggle(issue.id)}
                        className="w-4 h-4"
                        aria-label={`Select issue ${issue.id}`}
                      />
                    </td>
                    <td className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">
                      {issue.serial_title_name || `Title #${issue.serial_title_id}`}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-mono text-xs">
                      {issue.designation_override || issue.designation || `v${issue.volume ?? '?'}n${issue.number ?? '?'}`}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 tabular-nums">
                      {issue.expected_date}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 tabular-nums">
                      {issue.received_date || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[issue.status]}`}>
                        {STATUS_LABELS[issue.status]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {issue.branch_name || '—'}
                    </td>
                    <td className="px-4 py-3">
                      {issue.status === 'expected' && (
                        <div className="flex gap-1">
                          <button
                            onClick={async (e) => { e.stopPropagation(); try { await checkinSerialIssues({ issue_ids: [issue.id] }); toast.success('Received'); refresh() } catch { toast.error('Failed') } }}
                            className="px-2 py-1 text-xs rounded bg-status-success-600 text-white hover:bg-status-success-700"
                          >Receive</button>
                          {issue.expected_date && new Date(issue.expected_date) < new Date() && (
                            <button
                              onClick={async (e) => { e.stopPropagation(); try { await createSerialClaim(issue.id, { claim_type: 'not_received' }); toast.success('Claimed'); refresh() } catch { toast.error('Failed') } }}
                              className="px-2 py-1 text-xs rounded bg-status-warning-500 text-white hover:bg-status-warning-600"
                            >Claim</button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-lsc-border dark:border-earth-700 flex items-center justify-between text-sm">
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 rounded border border-lsc-border dark:border-earth-600 disabled:opacity-50 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 rounded border border-lsc-border dark:border-earth-600 disabled:opacity-50 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </AdminShell>
  )
}
