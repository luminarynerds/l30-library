/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Calendar, Play, Loader2, CheckCircle, XCircle, Clock } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'
import { AdminShell } from '../components/shells/AdminShell'
import { fairSchedulingApi } from '../api/fair-scheduling-api'
import { useBranchOptions } from '@/hooks/useBranchOptions'

interface Generation {
  id: number
  branch_id: number
  period_start: string
  period_end: string
  status: 'pending' | 'running' | 'optimal' | 'feasible' | 'infeasible' | 'timeout' | 'failed'
  objective_value: number | null
  solve_time_seconds: number | null
  total_shifts_assigned: number
  total_violations: number
  fairness_score: number | null
  constraint_summary: Record<string, unknown> | null
  is_published: boolean
  created_at?: string | null
}

const STATUS_BADGE: Record<Generation['status'], string> = {
  optimal: 'bg-lsc-green text-white',
  feasible: 'bg-status-warning-500 text-white',
  pending: 'bg-status-info-500 text-white',
  running: 'bg-status-info-500 text-white',
  infeasible: 'bg-status-danger-600 text-white',
  timeout: 'bg-status-danger-600 text-white',
  failed: 'bg-status-danger-600 text-white',
}

function StatusBadge({ status }: { status: Generation['status'] }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_BADGE[status]}`}>
      {status === 'running' && <Loader2 className="h-3 w-3 motion-safe:animate-spin" />}
      {status === 'optimal' && <CheckCircle className="h-3 w-3" />}
      {(status === 'infeasible' || status === 'failed') && <XCircle className="h-3 w-3" />}
      {(status === 'timeout') && <Clock className="h-3 w-3" />}
      {status}
    </span>
  )
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString()
}

export default function FairSchedulingGeneratePage(): React.ReactElement {
  const { user } = useAuth()
  const [generations, setGenerations] = useState<Generation[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [publishingId, setPublishingId] = useState<number | null>(null)
  const [confirmPublishId, setConfirmPublishId] = useState<number | null>(null)

  const [branchId, setBranchId] = useState(1)
  const { branches, loading: branchesLoading } = useBranchOptions()

  useEffect(() => {
    if (branches.length > 0 && !branches.some(b => b.id === branchId)) {
      setBranchId(branches[0]!.id)
    }
  }, [branches, branchId])
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')

  const loadGenerations = useCallback(async () => {
    try {
      const data = await fairSchedulingApi.getGenerations()
      setGenerations(Array.isArray(data) ? data : [])
    } catch {
      toast.error('Failed to load generation history')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadGenerations()
  }, [loadGenerations])

  if (!user || !['super_admin', 'admin', 'director'].includes(user.role)) {
    return (
      <AdminShell title="Schedule Generation">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          You do not have permission to access this page.
        </p>
      </AdminShell>
    )
  }

  const handleGenerate = async () => {
    if (!periodStart || !periodEnd) {
      toast.error('Please select both start and end dates')
      return
    }
    if (periodEnd <= periodStart) {
      toast.error('End date must be after start date')
      return
    }
    setGenerating(true)
    try {
      await fairSchedulingApi.generate({
        branch_id: branchId,
        period_start: periodStart,
        period_end: periodEnd,
      })
      toast.success('Schedule generation started')
      await loadGenerations()
    } catch {
      toast.error('Failed to start schedule generation')
    } finally {
      setGenerating(false)
    }
  }

  const handlePublish = async (id: number) => {
    setPublishingId(id)
    try {
      await fairSchedulingApi.publishGeneration(id)
      toast.success('Schedule published successfully')
      setConfirmPublishId(null)
      await loadGenerations()
    } catch {
      toast.error('Failed to publish schedule')
    } finally {
      setPublishingId(null)
    }
  }

  return (
    <AdminShell title="Schedule Generation" subtitle="Generate and publish fair schedules">
      {/* Generate Form */}
      <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6 mb-6">
        <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Calendar className="h-5 w-5" />
          Generate New Schedule
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label htmlFor="generate-branch" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Branch
            </label>
            <select
              id="generate-branch"
              value={branchId}
              onChange={(e) => setBranchId(Number(e.target.value))}
              disabled={branchesLoading}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2 text-sm"
            >
              {branchesLoading && <option value={branchId}>Loading branches...</option>}
              {branches.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Period Start
            </label>
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Period End
            </label>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div className="mt-4">
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {generating ? (
              <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {generating ? 'Generating...' : 'Generate Schedule'}
          </button>
        </div>
      </div>

      {/* Generations Table */}
      <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700">
          <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Generation History
          </h2>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : generations.length === 0 ? (
          <div className="px-6 py-12 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
            No generation runs yet. Use the form above to generate a schedule.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-lsc-border dark:border-earth-700 text-left text-lsc-dark/70 dark:text-lsc-cream/70">
                  <th className="px-4 py-3 font-medium">ID</th>
                  <th className="px-4 py-3 font-medium">Period</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Fairness</th>
                  <th className="px-4 py-3 font-medium">Shifts</th>
                  <th className="px-4 py-3 font-medium">Violations</th>
                  <th className="px-4 py-3 font-medium">Solve Time</th>
                  <th className="px-4 py-3 font-medium">Published</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="text-lsc-dark dark:text-lsc-cream">
                {generations.map((gen) => (
                  <tr
                    key={gen.id}
                    className="border-b border-lsc-border dark:border-earth-700 last:border-b-0"
                  >
                    <td className="px-4 py-3">{gen.id}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {formatDate(gen.period_start)} &ndash; {formatDate(gen.period_end)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={gen.status} />
                    </td>
                    <td className="px-4 py-3">
                      {gen.fairness_score != null ? gen.fairness_score.toFixed(2) : '-'}
                    </td>
                    <td className="px-4 py-3">{gen.total_shifts_assigned}</td>
                    <td className="px-4 py-3">{gen.total_violations}</td>
                    <td className="px-4 py-3">
                      {gen.solve_time_seconds != null ? `${gen.solve_time_seconds.toFixed(1)}s` : '-'}
                    </td>
                    <td className="px-4 py-3">
                      {gen.is_published ? (
                        <span className="inline-flex items-center gap-1 text-lsc-green">
                          <CheckCircle aria-hidden="true" className="h-4 w-4" />
                          Published
                        </span>
                      ) : (
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/40">
                          <span aria-hidden="true">-</span>
                          <span className="sr-only">Not published</span>
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {!gen.is_published && (gen.status === 'optimal' || gen.status === 'feasible') && (
                        <>
                          {confirmPublishId === gen.id ? (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handlePublish(gen.id)}
                                disabled={publishingId === gen.id}
                                className="inline-flex items-center gap-1 bg-lsc-green hover:bg-lsc-green/90 text-white rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-50 transition-colors"
                              >
                                {publishingId === gen.id ? (
                                  <Loader2 className="h-3 w-3 motion-safe:animate-spin" />
                                ) : (
                                  <CheckCircle className="h-3 w-3" />
                                )}
                                Confirm
                              </button>
                              <button
                                onClick={() => setConfirmPublishId(null)}
                                className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hover:underline"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setConfirmPublishId(gen.id)}
                              className="inline-flex items-center gap-1 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
                            >
                              Publish
                            </button>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminShell>
  )
}
