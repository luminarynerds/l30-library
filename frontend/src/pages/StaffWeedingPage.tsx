/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Loader2, Leaf, BarChart3, Check, X, Trash2,
  Copy, Clock, AlertTriangle, ArrowUpDown, Gift, Recycle,
  ChevronDown, ChevronRight, Archive, TrendingUp, Filter, Zap
} from "lucide-react"
import toast from "react-hot-toast"
import type {
  WeedingCandidate, WeedingSummary, SectionPressure,
  DuplicateGroup, SupersededEdition,
  WeedingStatus, WeedingReason, DisposalMethod,
} from "../api/weeding-api"
import * as weedingApi from "../api/weeding-api"
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { t } from '@/i18n'
import WeedingScheduleSettings from '../components/WeedingScheduleSettings'

// ============ Constants ============

const TABS = [
  { id: "dashboard", label: "Dashboard", icon: BarChart3 },
  { id: "candidates", label: "Candidates", icon: Leaf },
  { id: "sections", label: "Section Pressure", icon: Archive },
  { id: "duplicates", label: "Duplicates", icon: Copy },
  { id: "superseded", label: "Superseded", icon: ArrowUpDown },
]

const REASON_LABELS: Record<string, string> = {
  low_circulation: "Low Circulation",
  poor_condition: "Poor Condition",
  outdated: "Outdated Content",
  duplicate: "Duplicate",
  superseded: "Superseded Edition",
  damaged_beyond_repair: "Damaged",
  missing_long_term: "Missing Long-term",
  out_of_scope: "Out of Scope",
  never_circulated: "Never Circulated",
  space_pressure: "Space Pressure",
  other: "Other",
}

const STATUS_COLORS: Record<string, string> = {
  candidate: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300",
  under_review: "bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light",
  approved: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300",
  rejected: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300",
  disposed: "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70",
}

const DISPOSITION_LABELS: Record<string, { label: string; icon: typeof Gift }> = {
  donate_good_condition: { label: "Donate", icon: Gift },
  recycle_poor_condition: { label: "Recycle", icon: Recycle },
  sell_popular_title: { label: "Book Sale", icon: TrendingUp },
  transfer_to_branch: { label: "Transfer", icon: ArrowUpDown },
  discard: { label: "Discard", icon: Trash2 },
}

const CONDITION_COLORS: Record<string, string> = {
  new: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300",
  good: "bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light",
  fair: "bg-lsc-cream text-lsc-rose",
  poor: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300",
  damaged: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300",
  withdrawn: "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70",
}

// ============ Sub-components ============

function CrewScoreBadge({ score }: { score: number | null }) {
  if (score === null || score === undefined) return null
  let color = "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300"
  if (score >= 75) color = "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300"
  else if (score >= 50) color = "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300"
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      CREW {Math.round(score)}
    </span>
  )
}

function FillRateBar({ rate }: { rate: number }) {
  const pct = Math.min(100, Math.round(rate * 100))
  let barColor = "bg-status-success-500"
  if (rate > 1.0) barColor = "bg-status-danger-500"
  else if (rate > 0.85) barColor = "bg-status-warning-500"
  else if (rate > 0.7) barColor = "bg-status-warning-500"
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-earth-200 dark:bg-earth-700 rounded-full overflow-hidden">
        <div className={`h-full ${barColor} rounded-full transition-all`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 w-10 text-right">{pct}%</span>
    </div>
  )
}

// ============ Dashboard Tab ============

function DashboardTab({ summary, token, onRefresh }: { summary: WeedingSummary | null; token: string; onRefresh: () => void }) {
  const { t } = useTranslation();
  const [analyzing, setAnalyzing] = useState(false)

  const handleRunAnalysis = async () => {
    setAnalyzing(true)
    try {
      const result = await weedingApi.runAnalysis(token, { min_crew_score: 40, max_results: 200 })
      toast.success(t('toast.staffWeeding.analysisCompleteLengthNewCandidates', { length: result.items.length }))
      onRefresh()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.genealogyDocuments.analysisFailed'))
    } finally {
      setAnalyzing(false)
    }
  }

  if (!summary) return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-lg font-semibold text-earth-800 dark:text-earth-100">Weeding Dashboard</h2>
        <button
          onClick={handleRunAnalysis}
          disabled={analyzing}
          className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-green text-white rounded-lg hover:bg-status-success-700 disabled:opacity-50 transition-colors"
        >
          {analyzing ? <Loader2 className="h-4 w-4 motion-safe:animate-spin" /> : <Zap className="h-4 w-4" />}
          Run Smart Analysis
        </button>
      </div>
      <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
        <BarChart3 className="h-12 w-12 mx-auto mb-3 opacity-50" />
        <p className="font-medium mb-1">No weeding data available yet</p>
        <p className="text-sm">Run a Smart Analysis to generate weeding candidates and dashboard metrics.</p>
      </div>

      {/* Schedule Settings */}
      <div className="border-t border-lsc-border dark:border-earth-700 pt-6">
        <WeedingScheduleSettings token={token} onRunAnalysis={handleRunAnalysis} />
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-lg font-semibold text-earth-800 dark:text-earth-100">Weeding Dashboard</h2>
        <button
          onClick={handleRunAnalysis}
          disabled={analyzing}
          className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-green text-white rounded-lg hover:bg-status-success-700 disabled:opacity-50 transition-colors"
        >
          {analyzing ? <Loader2 className="h-4 w-4 motion-safe:animate-spin" /> : <Zap className="h-4 w-4" />}
          Run Smart Analysis
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-status-warning-100 dark:bg-status-warning-900/30 rounded-lg"><Leaf className="h-5 w-5 text-status-warning-600" /></div>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active Candidates</span>
          </div>
          <p className="text-2xl font-bold text-earth-800 dark:text-earth-100">{summary.total_candidates}</p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-status-danger-100 dark:bg-status-danger-900/30 rounded-lg"><AlertTriangle className="h-5 w-5 text-status-danger-600" /></div>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Outdated Content</span>
          </div>
          <p className="text-2xl font-bold text-earth-800 dark:text-earth-100">{summary.outdated_items}</p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-earth-100 dark:bg-earth-800/30 rounded-lg"><Copy className="h-5 w-5 text-lsc-rose dark:text-lsc-rose-light" /></div>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Excess Duplicates</span>
          </div>
          <p className="text-2xl font-bold text-earth-800 dark:text-earth-100">{summary.total_duplicates_excess}</p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-category-100 dark:bg-category-900/30 rounded-lg"><Clock className="h-5 w-5 text-category-600" /></div>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Never Circulated</span>
          </div>
          <p className="text-2xl font-bold text-earth-800 dark:text-earth-100">{summary.never_circulated_items}</p>
        </div>
      </div>

      {/* CREW Score & Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700">
          <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">Avg CREW Score</h3>
          <div className="flex items-end gap-3">
            <span className="text-4xl font-bold text-lsc-green">{summary.avg_crew_score !== null ? Math.round(summary.avg_crew_score) : "—"}</span>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">/ 100</span>
          </div>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('staffWeeding.higherScoresIndicateStrongerWeeding')}</p>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700">
          <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">By Reason</h3>
          <div className="space-y-2">
            {Object.entries(summary.by_reason).map(([reason, count]) => (
              <div key={reason} className="flex items-center justify-between">
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{REASON_LABELS[reason] || reason}</span>
                <span className="text-sm font-medium text-earth-800 dark:text-earth-100">{count}</span>
              </div>
            ))}
            {Object.keys(summary.by_reason).length === 0 && (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffWeeding.noActiveCandidatesRunAn')}</p>
            )}
          </div>
        </div>
      </div>

      {/* Sections over capacity */}
      {summary.sections_over_capacity > 0 && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-status-danger-600 flex-shrink-0" />
          <p className="text-sm text-status-danger-700 dark:text-status-danger-300">
            <strong>{summary.sections_over_capacity}</strong> section{summary.sections_over_capacity > 1 ? "s" : ""} over capacity.
            Review the Section Pressure tab to prioritize weeding.
          </p>
        </div>
      )}

      {/* Schedule Settings */}
      <div className="border-t border-lsc-border dark:border-earth-700 pt-6">
        <WeedingScheduleSettings token={token} onRunAnalysis={handleRunAnalysis} />
      </div>
    </div>
  )
}

// ============ Candidates Tab ============

function CandidatesTab({ token }: { token: string }) {
  const { t } = useTranslation();
  const [candidates, setCandidates] = useState<WeedingCandidate[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<WeedingStatus | "">("")
  const [reasonFilter, setReasonFilter] = useState<WeedingReason | "">("")
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const result = await weedingApi.listCandidates(token, clean({
        status: statusFilter || undefined,
        reason: reasonFilter || undefined,
        page,
        per_page: 25,
      }))
      setCandidates(result.items)
      setTotal(result.total)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffWeeding.failedToLoadCandidates'))
    } finally {
      setLoading(false)
    }
  }, [token, statusFilter, reasonFilter, page, t])

  useEffect(() => { load() }, [load])

  const handleReview = async (id: number, action: "approve" | "reject") => {
    try {
      await weedingApi.reviewCandidate(token, id, { action })
      toast.success(action === "approve" ? t('toast.staffWeeding.candidateApproved') : t('toast.staffWeeding.candidateRejected'))
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.dNALinksTab.reviewFailed'))
    }
  }

  const handleWithdraw = async (id: number, method: DisposalMethod) => {
    try {
      await weedingApi.withdrawCandidate(token, id, { disposal_method: method })
      toast.success(t('staffWeeding.itemWithdrawnFromCollection'))
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffWeeding.withdrawFailed'))
    }
  }

  const handleBatchApprove = async () => {
    if (selected.size === 0) return
    try {
      const result = await weedingApi.batchApprove(token, Array.from(selected))
      toast.success(t('toast.staffWeeding.approvedCandidatesApproved', { approved: result.approved }))
      setSelected(new Set())
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffWeeding.batchApproveFailed'))
    }
  }

  const handleBatchWithdraw = async (method: DisposalMethod) => {
    if (selected.size === 0) return
    try {
      const result = await weedingApi.batchWithdraw(token, Array.from(selected), method)
      toast.success(t('toast.staffWeeding.withdrawnItemsWithdrawn', { withdrawn: result.withdrawn }))
      setSelected(new Set())
      load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffWeeding.batchWithdrawFailed'))
    }
  }

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  const selectAll = () => {
    if (selected.size === candidates.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(candidates.map(c => c.id)))
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / 25))

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-earth-600" />
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value as WeedingStatus | ""); setPage(1) }}
            className="text-sm border border-lsc-border dark:border-earth-700 rounded-lg px-2 py-1.5 bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70"
          >
            <option value="">All Statuses</option>
            <option value="candidate">Candidate</option>
            <option value="under_review">Under Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="disposed">Disposed</option>
          </select>
        </div>
        <select
          value={reasonFilter}
          onChange={e => { setReasonFilter(e.target.value as WeedingReason | ""); setPage(1) }}
          className="text-sm border border-lsc-border dark:border-earth-700 rounded-lg px-2 py-1.5 bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70"
        >
          <option value="">All Reasons</option>
          {Object.entries(REASON_LABELS).map(([val, label]) => (
            <option key={val} value={val}>{label}</option>
          ))}
        </select>

        {/* Batch actions */}
        {selected.size > 0 && (
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{selected.size} selected</span>
            <button onClick={handleBatchApprove} className="text-xs px-3 py-1.5 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 transition-colors">
              Approve Selected
            </button>
            <button onClick={() => handleBatchWithdraw("donation")} className="text-xs px-3 py-1.5 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 transition-colors">
              Withdraw (Donate)
            </button>
            <button onClick={() => handleBatchWithdraw("recycling")} className="text-xs px-3 py-1.5 bg-earth-600 text-white rounded-lg hover:bg-earth-700 transition-colors">
              Withdraw (Recycle)
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="motion-safe:animate-spin h-8 w-8 text-lsc-green" /></div>
      ) : candidates.length === 0 ? (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
          <Leaf className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p className="mb-4">{t('staffWeeding.noWeedingCandidatesFoundRun')}</p>
          <button
            onClick={async () => {
              try {
                const result = await weedingApi.runAnalysis(token, { min_crew_score: 40, max_results: 200 })
                toast.success(t('toast.staffWeeding.analysisCompleteLengthNewCandidates', { length: result.items.length }))
                load()
              } catch (err: unknown) {
                toast.error(err instanceof Error ? err.message : t('toast.genealogyDocuments.analysisFailed'))
              }
            }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-green text-white rounded-lg hover:bg-status-success-700 transition-colors"
          >
            <Zap className="h-4 w-4" />
            Run Analysis
          </button>
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-earth-50 dark:bg-earth-900 border-b border-lsc-border dark:border-earth-700">
                <th className="w-8 px-3 py-2">
                  <input type="checkbox" checked={selected.size === candidates.length && candidates.length > 0} onChange={selectAll} className="rounded" />
                </th>
                <th className="text-left px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Item</th>
                <th className="text-left px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hidden md:table-cell">Reason</th>
                <th className="text-center px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hidden lg:table-cell">CREW</th>
                <th className="text-center px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hidden lg:table-cell">Checkouts</th>
                <th className="text-center px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                <th className="text-center px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hidden lg:table-cell">Disposition</th>
                <th className="w-28 px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map(c => (
                <CandidateRow
                  key={c.id}
                  candidate={c}
                  isSelected={selected.has(c.id)}
                  isExpanded={expandedId === c.id}
                  onToggleSelect={() => toggleSelect(c.id)}
                  onToggleExpand={() => setExpandedId(expandedId === c.id ? null : c.id)}
                  onApprove={() => handleReview(c.id, "approve")}
                  onReject={() => handleReview(c.id, "reject")}
                  onWithdraw={(method) => handleWithdraw(c.id, method)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Showing {((page - 1) * 25) + 1}-{Math.min(page * 25, total)} of {total}
          </span>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 text-sm border rounded-lg disabled:opacity-50 dark:border-earth-700 dark:text-earth-300">
              Previous
            </button>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="px-3 py-1 text-sm border rounded-lg disabled:opacity-50 dark:border-earth-700 dark:text-earth-300">
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function CandidateRow({
  candidate: c,
  isSelected,
  isExpanded,
  onToggleSelect,
  onToggleExpand,
  onApprove,
  onReject,
  onWithdraw,
}: {
  candidate: WeedingCandidate
  isSelected: boolean
  isExpanded: boolean
  onToggleSelect: () => void
  onToggleExpand: () => void
  onApprove: () => void
  onReject: () => void
  onWithdraw: (method: DisposalMethod) => void
}) {
  const { t } = useTranslation()
  const dispInfo = c.disposition_recommendation ? DISPOSITION_LABELS[c.disposition_recommendation] : null

  return (
    <>
      <tr className="border-b border-earth-100 dark:border-earth-700/50 hover:bg-earth-50 dark:hover:bg-earth-700/30 transition-colors">
        <td className="px-3 py-2">
          <input type="checkbox" checked={isSelected} onChange={onToggleSelect} className="rounded" />
        </td>
        <td className="px-3 py-2">
          <button onClick={onToggleExpand} className="flex items-start gap-2 text-left">
            {isExpanded ? <ChevronDown className="h-4 w-4 mt-0.5 text-earth-600 flex-shrink-0" /> : <ChevronRight className="h-4 w-4 mt-0.5 text-earth-600 flex-shrink-0" />}
            <div>
              <p className="font-medium text-earth-800 dark:text-earth-100">{c.item_title || "Unknown"}</p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{c.item_author} {c.item_barcode ? `· ${c.item_barcode}` : ""}</p>
            </div>
          </button>
        </td>
        <td className="px-3 py-2 hidden md:table-cell">
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{REASON_LABELS[c.reason] || c.reason}</span>
        </td>
        <td className="px-3 py-2 text-center hidden lg:table-cell">
          <CrewScoreBadge score={c.crew_score} />
        </td>
        <td className="px-3 py-2 text-center hidden lg:table-cell">
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{c.total_checkouts}</span>
        </td>
        <td className="px-3 py-2 text-center">
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[c.status] || ""}`}>
            {c.status.replace("_", " ")}
          </span>
        </td>
        <td className="px-3 py-2 text-center hidden lg:table-cell">
          {dispInfo && (
            <span className="inline-flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              <dispInfo.icon className="h-3 w-3" />
              {dispInfo.label}
            </span>
          )}
        </td>
        <td className="px-3 py-2 text-right">
          <div className="flex items-center justify-end gap-1">
            {(c.status === "candidate" || c.status === "under_review") && (
              <>
                <button onClick={onApprove} title="Approve" className="p-1.5 text-status-success-600 hover:bg-status-success-50 dark:hover:bg-status-success-900/20 rounded-lg transition-colors">
                  <Check className="h-4 w-4" />
                </button>
                <button onClick={onReject} title="Reject" className="p-1.5 text-status-danger-600 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded-lg transition-colors">
                  <X className="h-4 w-4" />
                </button>
              </>
            )}
            {c.status === "approved" && (
              <button
                onClick={() => onWithdraw(c.disposition_recommendation === "recycle_poor_condition" ? "recycling" : c.disposition_recommendation === "sell_popular_title" ? "sale" : "donation")}
                title="Withdraw"
                className="p-1.5 text-status-warning-600 hover:bg-status-warning-50 dark:hover:bg-status-warning-900/20 rounded-lg transition-colors"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        </td>
      </tr>
      {isExpanded && (
        <tr className="bg-earth-50/50 dark:bg-earth-900/30">
          <td colSpan={8} className="px-6 py-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="space-y-1">
                <p className="font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Item Details</p>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Location: {c.item_location || "N/A"}</p>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Type: {c.item_type || "N/A"}</p>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Condition: <span className={`inline-flex items-center px-1.5 rounded text-xs ${CONDITION_COLORS[c.item_condition || ""] || ""}`}>{c.item_condition || "N/A"}</span></p>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Published: {c.publication_year || "N/A"}</p>
                {c.isbn && <p className="text-lsc-dark/70 dark:text-lsc-cream/70">ISBN: {c.isbn}</p>}
              </div>
              <div className="space-y-1">
                <p className="font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Circulation</p>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Total Checkouts: {c.total_checkouts}</p>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Last Checkout: {c.last_checkout_date || "Never"}</p>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Age: {c.years_since_acquisition ? c.years_since_acquisition + " years" : "N/A"}</p>
                {c.never_circulated && <p className="text-status-danger-600 dark:text-status-danger-400 font-medium">{t('staffWeeding.neverCirculatedSinceAcquisition')}</p>}
              </div>
              <div className="space-y-1">
                <p className="font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Analysis</p>
                {c.crew_category && <p className="text-lsc-dark/70 dark:text-lsc-cream/70">CREW Category: {c.crew_category}</p>}
                {c.is_outdated_content && <p className="text-status-warning-600 dark:text-status-warning-400">Outdated content flagged</p>}
                {c.is_duplicate && <p className="text-lsc-rose dark:text-lsc-rose-light">Duplicate ({c.duplicate_count} copies)</p>}
                {c.is_superseded && <p className="text-category-600 dark:text-category-400">Newer edition available</p>}
                {c.disposition_rationale && <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-xs mt-1">{c.disposition_rationale}</p>}
              </div>
            </div>
            {c.reason_notes && (
              <div className="mt-3 p-3 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Analysis Notes</p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{c.reason_notes}</p>
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

// ============ Section Pressure Tab ============

function SectionPressureTab({ token }: { token: string }) {
  const { t } = useTranslation();
  const [sections, setSections] = useState<SectionPressure[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    weedingApi.getSectionPressure(token)
      .then(r => setSections(r.sections))
      .catch(() => toast.error(t('staffWeeding.failedToLoadSectionData')))
      .finally(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="motion-safe:animate-spin h-8 w-8 text-lsc-green" /></div>

  return (
    <div className="space-y-4">
      <h2 className="font-serif text-lg font-semibold text-earth-800 dark:text-earth-100">{t('staffWeeding.spacePressureBySection')}</h2>
      {sections.length === 0 ? (
        <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-8">{t('staffWeeding.noSectionDataAvailable')}</p>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-earth-50 dark:bg-earth-900 border-b border-lsc-border dark:border-earth-700">
                <th className="text-left px-4 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Section</th>
                <th className="text-center px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Items</th>
                <th className="text-left px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70 w-40">Fill Rate</th>
                <th className="text-center px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hidden md:table-cell">Avg Age</th>
                <th className="text-center px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hidden md:table-cell">Avg Checkouts</th>
                <th className="text-center px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hidden lg:table-cell">Low Circ</th>
                <th className="text-center px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Weeding</th>
              </tr>
            </thead>
            <tbody>
              {sections.map(s => (
                <tr key={s.location} className="border-b border-earth-100 dark:border-earth-700/50 hover:bg-earth-50 dark:hover:bg-earth-700/30 transition-colors">
                  <td className="px-4 py-2 font-medium text-earth-800 dark:text-earth-100">{s.location}</td>
                  <td className="px-3 py-2 text-center text-lsc-dark/70 dark:text-lsc-cream/70">{s.total_items}</td>
                  <td className="px-3 py-2"><FillRateBar rate={s.fill_rate} /></td>
                  <td className="px-3 py-2 text-center text-lsc-dark/70 dark:text-lsc-cream/70 hidden md:table-cell">{s.avg_item_age_years} yr</td>
                  <td className="px-3 py-2 text-center text-lsc-dark/70 dark:text-lsc-cream/70 hidden md:table-cell">{s.avg_checkouts}</td>
                  <td className="px-3 py-2 text-center text-lsc-dark/70 dark:text-lsc-cream/70 hidden lg:table-cell">{s.low_circ_items}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`text-sm font-medium ${s.weeding_candidates_count > 0 ? "text-status-warning-600 dark:text-status-warning-400" : "text-earth-600"}`}>
                      {s.weeding_candidates_count}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ============ Duplicates Tab ============

function DuplicatesTab({ token }: { token: string }) {
  const { t } = useTranslation();
  const [groups, setGroups] = useState<DuplicateGroup[]>([])
  const [totalExcess, setTotalExcess] = useState(0)
  const [loading, setLoading] = useState(false)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    setLoading(true)
    weedingApi.getDuplicates(token)
      .then(r => { setGroups(r.groups); setTotalExcess(r.total_excess_copies) })
      .catch(() => toast.error(t('staffWeeding.failedToLoadDuplicateData')))
      .finally(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="motion-safe:animate-spin h-8 w-8 text-lsc-green" /></div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-lg font-semibold text-earth-800 dark:text-earth-100">Duplicate Detection</h2>
        {totalExcess > 0 && (
          <span className="text-sm text-status-warning-600 dark:text-status-warning-400">{totalExcess} excess copies identified</span>
        )}
      </div>
      {groups.length === 0 ? (
        <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-8">{t('staffWeeding.noExcessDuplicatesDetected')}</p>
      ) : (
        <div className="space-y-3">
          {groups.map(g => (
            <div key={g.catalog_item_id} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
              <button
                onClick={() => setExpandedId(expandedId === g.catalog_item_id ? null : g.catalog_item_id)}
                className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-earth-50 dark:hover:bg-earth-700/30 transition-colors rounded-xl"
              >
                <div className="flex items-center gap-3">
                  {expandedId === g.catalog_item_id ? <ChevronDown className="h-4 w-4 text-earth-600" /> : <ChevronRight className="h-4 w-4 text-earth-600" />}
                  <div>
                    <p className="font-medium text-earth-800 dark:text-earth-100">{g.title}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{g.author}{g.isbn ? ` · ISBN: ${g.isbn}` : ""}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{g.total_copies} copies</span>
                  {g.excess_copies > 0 && (
                    <span className="text-xs px-2 py-0.5 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300 rounded">
                      {g.excess_copies} excess
                    </span>
                  )}
                </div>
              </button>
              {expandedId === g.catalog_item_id && (
                <div className="px-4 pb-3">
                  <div className="space-y-1">
                    {g.copies.map(copy => (
                      <div key={copy.id} className="flex items-center justify-between py-1.5 px-3 bg-earth-50 dark:bg-earth-900/30 rounded-lg text-sm">
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-xs text-earth-600">{copy.barcode}</span>
                          <span className={`inline-flex items-center px-1.5 rounded text-xs ${CONDITION_COLORS[copy.condition] || ""}`}>{copy.condition}</span>
                        </div>
                        <span className="text-xs text-earth-600">{copy.location || "No location"}</span>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                    Recommended: keep {g.recommended_copies} copies, consider weeding {g.excess_copies}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ============ Superseded Tab ============

function SupersededTab({ token }: { token: string }) {
  const { t } = useTranslation();
  const [items, setItems] = useState<SupersededEdition[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    weedingApi.getSupersededEditions(token)
      .then(r => setItems(r.items))
      .catch(() => toast.error(t('staffWeeding.failedToLoadSupersededEditions')))
      .finally(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="motion-safe:animate-spin h-8 w-8 text-lsc-green" /></div>

  return (
    <div className="space-y-4">
      <h2 className="font-serif text-lg font-semibold text-earth-800 dark:text-earth-100">Superseded Editions</h2>
      {items.length === 0 ? (
        <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-8">{t('staffWeeding.noSupersededEditionsDetected')}</p>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-earth-50 dark:bg-earth-900 border-b border-lsc-border dark:border-earth-700">
                <th className="text-left px-4 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Older Edition</th>
                <th className="text-center px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hidden md:table-cell">Year</th>
                <th className="text-center px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70"><ArrowUpDown className="h-4 w-4 mx-auto" /></th>
                <th className="text-left px-4 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Newer Edition</th>
                <th className="text-center px-3 py-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hidden md:table-cell">Year</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr key={idx} className="border-b border-earth-100 dark:border-earth-700/50 hover:bg-earth-50 dark:hover:bg-earth-700/30 transition-colors">
                  <td className="px-4 py-2">
                    <p className="text-earth-800 dark:text-earth-100">{item.older_title}</p>
                    {item.older_edition && <p className="text-xs text-earth-600">{item.older_edition}</p>}
                  </td>
                  <td className="px-3 py-2 text-center text-earth-600 hidden md:table-cell">{item.older_publication_year || "—"}</td>
                  <td className="px-3 py-2 text-center"><ArrowUpDown className="h-4 w-4 mx-auto text-earth-300" /></td>
                  <td className="px-4 py-2">
                    <p className="text-status-success-700 dark:text-status-success-400">{item.newer_title}</p>
                    {item.newer_edition && <p className="text-xs text-status-success-500 dark:text-status-success-500">{item.newer_edition}</p>}
                  </td>
                  <td className="px-3 py-2 text-center text-status-success-600 hidden md:table-cell">{item.newer_publication_year || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ============ Main Page ============

export default function StaffWeedingPage(): React.ReactElement {
  const { user, token, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState("dashboard")
  const [summary, setSummary] = useState<WeedingSummary | null>(null)

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, user, navigate])

  const [_summaryError, setSummaryError] = useState(false)

  const loadSummary = useCallback(async () => {
    if (!token) return
    try {
      setSummaryError(false)
      const data = await weedingApi.getSummary(token)
      setSummary(data)
    } catch {
      setSummaryError(true)
    }
  }, [token])

  // eslint-disable-next-line react-hooks/set-state-in-effect -- loadSummary is an async fetch; the synchronous setSummaryError(false) just resets the error flag before the request
  useEffect(() => { loadSummary() }, [loadSummary])

  if (authLoading || !token) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <Loader2 className="motion-safe:animate-spin h-8 w-8 text-lsc-green" />
      </div>
    )
  }

  return (
    <AdminShell title="Smart Weeding" subtitle="CREW method-based collection analysis. Take the guesswork out of weeding.">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 bg-lsc-green/10 rounded-lg">
              <Leaf className="h-6 w-6 text-lsc-green" />
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-1 mb-6 bg-lsc-white dark:bg-earth-800 rounded-xl p-1 border border-lsc-border dark:border-earth-700 overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-lsc-green text-white"
                  : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700"
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === "dashboard" && <DashboardTab summary={summary} token={token} onRefresh={loadSummary} />}
        {activeTab === "candidates" && <CandidatesTab token={token} />}
        {activeTab === "sections" && <SectionPressureTab token={token} />}
        {activeTab === "duplicates" && <DuplicatesTab token={token} />}
        {activeTab === "superseded" && <SupersededTab token={token} />}

    </AdminShell>
  )
}
