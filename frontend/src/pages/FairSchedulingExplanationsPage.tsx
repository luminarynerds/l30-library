/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Info, Search, User, FileText, Loader2 } from 'lucide-react'
import { AdminShell } from '../components/shells'
import { fairSchedulingApi } from '../api/fair-scheduling-api'
import toast from 'react-hot-toast'

interface ScheduleExplanation {
  id: number
  generation_id: number
  shift_id: number
  staff_id: number
  explanation_type: string
  explanation_text: string
  contributing_factors: Record<string, unknown>[]
  fairness_impact: number
  created_at?: string | null
}

interface StaffScheduleExplanation {
  staff_id: number
  staff_name: string
  total_shifts: number
  total_hours: number
  fairness_score: number
  explanations: ScheduleExplanation[]
  preference_honor_rate: number
  top_factors: string[]
}

interface Generation {
  id: number
  created_at?: string
  status?: string
  [key: string]: unknown
}

type ViewMode = 'generation' | 'staff'

function getTypeBadgeClasses(type: string): string {
  const t = type.toLowerCase()
  if (t.includes('preference')) return 'bg-lsc-green text-white'
  if (t.includes('coverage')) return 'bg-lsc-rose text-white'
  if (t.includes('fairness')) return 'bg-status-info-500 text-white'
  return 'bg-earth-600 text-white'
}

// Human-readable labels for the contributing-factor keys emitted by the
// constraint solver (backend constraint_schedule_solver.py). Unknown keys fall
// back to a humanized version of the raw key so new factors stay readable.
const FACTOR_LABELS: Record<string, string> = {
  preference_match: 'Matched their preferences',
  fairness_balance: 'Balanced their workload',
  skill_coverage: 'Covered a needed skill',
  fatigue_prevention: 'Avoided overworking them',
}

function humanizeFactorKey(key: string): string {
  const cleaned = key.replace(/[_-]+/g, ' ').trim()
  if (!cleaned) return 'Factor'
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1)
}

function factorLabel(key: string): string {
  return FACTOR_LABELS[key] ?? humanizeFactorKey(key)
}

function ExplanationTable({ explanations }: { explanations: ScheduleExplanation[] }) {
  if (explanations.length === 0) {
    return (
      <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
        <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>No explanations found.</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead className="text-xs uppercase text-lsc-dark/70 dark:text-lsc-cream/70 border-b border-lsc-border dark:border-earth-700">
          <tr>
            <th className="px-4 py-3">Staff ID</th>
            <th className="px-4 py-3">Shift ID</th>
            <th className="px-4 py-3">Type</th>
            <th className="px-4 py-3">Explanation</th>
            <th className="px-4 py-3">Fairness Impact</th>
            <th className="px-4 py-3">Factors</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
          {explanations.map((exp) => (
            <tr key={exp.id} className="text-lsc-dark dark:text-lsc-cream">
              <td className="px-4 py-3 font-mono">{exp.staff_id}</td>
              <td className="px-4 py-3 font-mono">{exp.shift_id}</td>
              <td className="px-4 py-3">
                <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${getTypeBadgeClasses(exp.explanation_type)}`}>
                  {exp.explanation_type}
                </span>
              </td>
              <td className="px-4 py-3 max-w-md">{exp.explanation_text}</td>
              <td className="px-4 py-3">
                <span className={exp.fairness_impact >= 0 ? 'text-lsc-green' : 'text-status-danger-500'}>
                  {exp.fairness_impact >= 0 ? '+' : ''}{exp.fairness_impact.toFixed(2)}
                </span>
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap gap-1">
                  {exp.contributing_factors.slice(0, 3).map((factor, i) => {
                    const key = typeof factor.factor === 'string' ? factor.factor : (Object.keys(factor)[0] ?? '')
                    const detail = typeof factor.detail === 'string' ? factor.detail : undefined
                    return (
                      <span
                        key={i}
                        title={detail}
                        className="rounded-full px-2.5 py-1 text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      >
                        {factorLabel(key)}
                      </span>
                    )
                  })}
                  {exp.contributing_factors.length > 3 && (
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      +{exp.contributing_factors.length - 3} more
                    </span>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function FairSchedulingExplanationsPage(): React.ReactElement {
  const [activeView, setActiveView] = useState<ViewMode>('generation')
  const [loading, setLoading] = useState(false)

  // Generation view state
  const [generations, setGenerations] = useState<Generation[]>([])
  const [selectedGenerationId, setSelectedGenerationId] = useState<number | null>(null)
  const [explanations, setExplanations] = useState<ScheduleExplanation[]>([])

  // Staff view state
  const [staffIdInput, setStaffIdInput] = useState('')
  const [staffExplanation, setStaffExplanation] = useState<StaffScheduleExplanation | null>(null)

  const loadGenerations = useCallback(async () => {
    try {
      const data = await fairSchedulingApi.getGenerations()
      setGenerations(Array.isArray(data) ? data : data?.data ?? [])
    } catch {
      toast.error('Failed to load generations')
    }
  }, [])

  useEffect(() => {
    loadGenerations()
  }, [loadGenerations])

  const loadExplanations = useCallback(async (genId: number) => {
    setLoading(true)
    try {
      const data = await fairSchedulingApi.getExplanations(genId)
      setExplanations(Array.isArray(data) ? data : data?.data ?? [])
    } catch {
      toast.error('Failed to load explanations')
      setExplanations([])
    } finally {
      setLoading(false)
    }
  }, [])

  const handleGenerationChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = Number(e.target.value)
    if (id) {
      setSelectedGenerationId(id)
      loadExplanations(id)
    } else {
      setSelectedGenerationId(null)
      setExplanations([])
    }
  }, [loadExplanations])

  const lookUpStaff = useCallback(async () => {
    const id = Number(staffIdInput)
    if (!id || id <= 0) {
      toast.error('Enter a valid staff ID')
      return
    }
    setLoading(true)
    try {
      const data = await fairSchedulingApi.getStaffExplanation(id)
      setStaffExplanation(data?.data ?? data)
    } catch {
      toast.error('Failed to load staff explanation')
      setStaffExplanation(null)
    } finally {
      setLoading(false)
    }
  }, [staffIdInput])

  return (
    <AdminShell title="Schedule Explanations" subtitle="Understand why shifts were assigned">
      {/* View toggle */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveView('generation')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeView === 'generation'
              ? 'bg-lsc-rose text-white'
              : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
          }`}
        >
          <FileText className="h-4 w-4" />
          By Generation
        </button>
        <button
          onClick={() => setActiveView('staff')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeView === 'staff'
              ? 'bg-lsc-rose text-white'
              : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
          }`}
        >
          <User className="h-4 w-4" />
          By Staff Member
        </button>
      </div>

      {/* By Generation view */}
      {activeView === 'generation' && (
        <div className="space-y-4">
          <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Select Generation Run
            </label>
            <select
              value={selectedGenerationId ?? ''}
              onChange={handleGenerationChange}
              className="w-full max-w-md rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2 text-sm"
            >
              <option value="">-- Choose a generation --</option>
              {generations.map((gen) => (
                <option key={gen.id} value={gen.id}>
                  Generation #{gen.id}{gen.created_at ? ` - ${new Date(gen.created_at).toLocaleDateString()}` : ''}{gen.status ? ` (${gen.status})` : ''}
                </option>
              ))}
            </select>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-rose" />
            </div>
          ) : selectedGenerationId ? (
            <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
                <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                  <Info className="h-4 w-4 text-lsc-rose" />
                  {explanations.length} explanation{explanations.length !== 1 ? 's' : ''} for Generation #{selectedGenerationId}
                </h3>
              </div>
              <ExplanationTable explanations={explanations} />
            </div>
          ) : null}
        </div>
      )}

      {/* By Staff view */}
      {activeView === 'staff' && (
        <div className="space-y-4">
          <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Staff ID
            </label>
            <div className="flex gap-2 max-w-md">
              <input
                type="number"
                min={1}
                value={staffIdInput}
                onChange={(e) => setStaffIdInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && lookUpStaff()}
                placeholder="Enter staff ID"
                className="flex-1 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2 text-sm"
              />
              <button
                onClick={lookUpStaff}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                <Search className="h-4 w-4" />
                Look Up
              </button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-rose" />
            </div>
          ) : staffExplanation ? (
            <div className="space-y-4">
              {/* Staff summary card */}
              <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6">
                <div className="flex items-start gap-3 mb-4">
                  <User className="h-5 w-5 text-lsc-rose mt-0.5" />
                  <div>
                    <h3 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                      {staffExplanation.staff_name}
                    </h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      Staff ID: {staffExplanation.staff_id}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Total Shifts</p>
                    <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">{staffExplanation.total_shifts}</p>
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Total Hours</p>
                    <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">{staffExplanation.total_hours}</p>
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Fairness Score</p>
                    <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">{staffExplanation.fairness_score.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Preference Honor Rate</p>
                    <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">{(staffExplanation.preference_honor_rate * 100).toFixed(0)}%</p>
                  </div>
                </div>

                {staffExplanation.top_factors.length > 0 && (
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-2">Top Factors</p>
                    <div className="flex flex-wrap gap-2">
                      {staffExplanation.top_factors.map((factor, i) => (
                        <span key={i} className="rounded-full px-2.5 py-1 text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream">
                          {factorLabel(factor)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Staff explanations table */}
              <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
                <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
                  <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                    <FileText className="h-4 w-4 text-lsc-rose" />
                    {staffExplanation.explanations.length} shift explanation{staffExplanation.explanations.length !== 1 ? 's' : ''}
                  </h3>
                </div>
                <ExplanationTable explanations={staffExplanation.explanations} />
              </div>
            </div>
          ) : null}
        </div>
      )}
    </AdminShell>
  )
}
