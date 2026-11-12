/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Calendar,
  AlertTriangle,
  Users,
  DollarSign,
  ArrowRight,
  CalendarOff,
  Shield,
  CheckCircle2,
  Clock,
} from 'lucide-react'
import { RadialBarChart, RadialBar, ResponsiveContainer } from 'recharts'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'
import { useTranslation } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { fairSchedulingApi } from '../api/fair-scheduling-api'

interface DashboardData {
  current_generation: {
    id: number
    branch_id: number
    period_start: string
    period_end: string
    status:
      | 'pending'
      | 'running'
      | 'optimal'
      | 'feasible'
      | 'infeasible'
      | 'timeout'
      | 'failed'
    fairness_score: number | null
    total_shifts_assigned: number
    total_violations: number
    is_published: boolean
    created_at?: string | null
  } | null
  overall_fairness_score: number
  staff_fairness: Record<string, unknown>[]
  fatigue_summary: Record<string, unknown>
  open_callouts: Array<{
    id: number
    callout_reason: string | null
    shift_date: string
    status:
      | 'open'
      | 'searching'
      | 'covered'
      | 'partial'
      | 'uncovered'
      | 'cancelled'
    urgency: 'low' | 'medium' | 'high' | 'emergency'
  }>
  preference_insights: Record<string, unknown>
  payroll_status: Record<string, unknown>
  upcoming_highlights: Record<string, unknown>[]
}

const GENERATION_STATUS_COLORS: Record<string, string> = {
  optimal: 'bg-lsc-green text-white',
  feasible: 'bg-status-warning-500 text-white',
  pending: 'bg-status-info-500 text-white',
  running: 'bg-status-info-500 text-white',
  infeasible: 'bg-status-danger-600 text-white',
  timeout: 'bg-status-danger-600 text-white',
  failed: 'bg-status-danger-600 text-white',
}

const URGENCY_COLORS: Record<string, string> = {
  emergency: 'bg-status-danger-600 text-white',
  high: 'bg-lsc-rose text-white',
  medium: 'bg-status-warning-500 text-white',
  low: 'bg-earth-400 dark:bg-earth-500 text-white',
}

const FATIGUE_COLORS: Record<string, string> = {
  critical: 'bg-status-danger-600 text-white',
  high: 'bg-lsc-rose text-white',
  moderate: 'bg-status-warning-500 text-white',
  low: 'bg-lsc-green text-white',
}

function getFairnessColor(score: number): string {
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#eab308'
  return '#dc2626'
}

function getFairnessLabel(score: number): string {
  if (score >= 80) return 'Good'
  if (score >= 60) return 'Fair'
  return 'Needs Attention'
}

function StatusBadge({
  label,
  colorClass,
}: {
  label: string
  colorClass: string
}) {
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  )
}

export default function FairSchedulingDashboardPage(): React.ReactElement {
  const { user } = useAuth()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user || !['super_admin', 'admin', 'director'].includes(user.role)) {
      navigate('/')
      return
    }

    let cancelled = false
    const loadDashboard = async () => {
      try {
        const response = await fairSchedulingApi.getDashboard()
        if (!cancelled) {
          setData(response.data ?? response)
        }
      } catch {
        if (!cancelled) {
          toast.error(t('error.generic', 'Failed to load dashboard data'))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }
    loadDashboard()
    return () => {
      cancelled = true
    }
  }, [user, navigate, t])

  if (loading) {
    return (
      <AdminShell title="Fair Scheduling Dashboard" loading>
        <div />
      </AdminShell>
    )
  }

  if (!data) {
    return (
      <AdminShell
        title="Fair Scheduling Dashboard"
        subtitle="Overview of schedule fairness, fatigue, and operations"
      >
        <div className="flex flex-col items-center justify-center h-64 text-lsc-dark/70 dark:text-lsc-cream/70">
          <CalendarOff className="h-12 w-12 mb-4" />
          <p className="text-lg">Unable to load dashboard data.</p>
        </div>
      </AdminShell>
    )
  }

  const fairnessScore = data.overall_fairness_score ?? 0
  const fairnessColor = getFairnessColor(fairnessScore)
  const chartData = [
    { name: 'score', value: fairnessScore, fill: fairnessColor },
  ]

  const fatigueSummary = data.fatigue_summary as Record<string, number>
  const payrollStatus = data.payroll_status as Record<string, unknown>
  const openCallouts = data.open_callouts ?? []

  return (
    <AdminShell
      title="Fair Scheduling Dashboard"
      subtitle="Overview of schedule fairness, fatigue, and operations"
    >
      {/* Top row: Fairness + Current Generation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Overall Fairness Score */}
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6 flex flex-col items-center">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Overall Fairness
          </h2>
          <div className="w-48 h-48">
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart
                cx="50%"
                cy="50%"
                innerRadius="70%"
                outerRadius="100%"
                startAngle={180}
                endAngle={0}
                data={chartData}
                barSize={16}
              >
                <RadialBar
                  background={{ fill: 'rgba(128,128,128,0.15)' }}
                  dataKey="value"
                  cornerRadius={8}
                />
              </RadialBarChart>
            </ResponsiveContainer>
          </div>
          <div className="-mt-16 text-center">
            <span
              className="text-4xl font-bold"
              style={{ color: fairnessColor }}
            >
              {fairnessScore}
            </span>
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
              /100
            </span>
          </div>
          <p
            className="mt-2 text-sm font-medium"
            style={{ color: fairnessColor }}
          >
            {getFairnessLabel(fairnessScore)}
          </p>
        </div>

        {/* Current Generation */}
        <div className="lg:col-span-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Current Schedule Generation
            </h2>
            <button
              onClick={() => navigate('/staff/fair-scheduling/generate')}
              className="text-sm text-lsc-rose hover:text-lsc-rose/80 flex items-center gap-1"
            >
              Manage <ArrowRight className="h-4 w-4" />
            </button>
          </div>

          {data.current_generation ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <StatusBadge
                  label={data.current_generation.status}
                  colorClass={
                    GENERATION_STATUS_COLORS[data.current_generation.status] ??
                    'bg-earth-400 dark:bg-earth-500 text-white'
                  }
                />
                {data.current_generation.is_published ? (
                  <StatusBadge
                    label="Published"
                    colorClass="bg-lsc-green text-white"
                  />
                ) : (
                  <StatusBadge
                    label="Draft"
                    colorClass="bg-earth-400 dark:bg-earth-500 text-white"
                  />
                )}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    Period
                  </p>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                    {data.current_generation.period_start} &mdash;{' '}
                    {data.current_generation.period_end}
                  </p>
                </div>
                <div>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    Shifts Assigned
                  </p>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                    {data.current_generation.total_shifts_assigned}
                  </p>
                </div>
                <div>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    Violations
                  </p>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                    {data.current_generation.total_violations}
                  </p>
                </div>
                <div>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    Fairness Score
                  </p>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                    {data.current_generation.fairness_score != null
                      ? data.current_generation.fairness_score
                      : 'N/A'}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-40 text-lsc-dark/70 dark:text-lsc-cream/70">
              <CalendarOff className="h-10 w-10 mb-3" />
              <p>No schedule generated yet</p>
              <button
                onClick={() => navigate('/staff/fair-scheduling/generate')}
                className="mt-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 text-sm font-medium"
              >
                Generate Schedule
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Second row: Fatigue + Call-Outs + Payroll */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* Fatigue Summary */}
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Fatigue Summary
            </h2>
            <button
              onClick={() => navigate('/staff/fair-scheduling/fatigue')}
              className="text-sm text-lsc-rose hover:text-lsc-rose/80 flex items-center gap-1"
            >
              Details <ArrowRight className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-3">
            {['critical', 'high', 'moderate', 'low'].map((level) => {
              const count =
                fatigueSummary[level] ?? fatigueSummary[`${level}_count`] ?? 0
              return (
                <div
                  key={level}
                  className="flex items-center justify-between"
                >
                  <StatusBadge
                    label={level.charAt(0).toUpperCase() + level.slice(1)}
                    colorClass={FATIGUE_COLORS[level] ?? "bg-earth-400 text-white"}
                  />
                  <span className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    {Number(count)}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Open Call-Outs */}
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Open Call-Outs
            </h2>
            <button
              onClick={() => navigate('/staff/fair-scheduling/call-outs')}
              className="text-sm text-lsc-rose hover:text-lsc-rose/80 flex items-center gap-1"
            >
              View All <ArrowRight className="h-4 w-4" />
            </button>
          </div>

          {openCallouts.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-lsc-dark/70 dark:text-lsc-cream/70">
              <CheckCircle2 className="h-8 w-8 mb-2 text-lsc-green" />
              <p className="text-sm">No open call-outs</p>
            </div>
          ) : (
            <>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream mb-3">
                {openCallouts.length}
              </p>
              <ul className="space-y-2 max-h-40 overflow-y-auto">
                {openCallouts.slice(0, 5).map((callout) => (
                  <li
                    key={callout.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-lsc-dark dark:text-lsc-cream truncate mr-2">
                      {callout.shift_date}
                      {callout.callout_reason
                        ? ` \u2014 ${callout.callout_reason}`
                        : ''}
                    </span>
                    <StatusBadge
                      label={callout.urgency}
                      colorClass={
                        URGENCY_COLORS[callout.urgency] ??
                        'bg-earth-400 dark:bg-earth-500 text-white'
                      }
                    />
                  </li>
                ))}
              </ul>
              {openCallouts.length > 5 && (
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                  +{openCallouts.length - 5} more
                </p>
              )}
            </>
          )}
        </div>

        {/* Payroll Status */}
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Payroll Status
            </h2>
            <button
              onClick={() => navigate('/staff/fair-scheduling/payroll')}
              className="text-sm text-lsc-rose hover:text-lsc-rose/80 flex items-center gap-1"
            >
              Details <ArrowRight className="h-4 w-4" />
            </button>
          </div>

          {Object.keys(payrollStatus).length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-lsc-dark/70 dark:text-lsc-cream/70">
              <Clock className="h-8 w-8 mb-2" />
              <p className="text-sm">No payroll data</p>
            </div>
          ) : (
            <dl className="space-y-2">
              {Object.entries(payrollStatus).map(([key, value]) => (
                <div key={key} className="flex justify-between text-sm">
                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                    {key.replace(/_/g, ' ')}
                  </dt>
                  <dd className="font-medium text-lsc-dark dark:text-lsc-cream">
                    {String(value)}
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>

      {/* Staff Fairness Table */}
      {data.staff_fairness.length > 0 && (
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
            <Users className="h-5 w-5" />
            Staff Fairness
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-lsc-border dark:border-earth-700">
                  {data.staff_fairness.length > 0 &&
                    Object.keys(data.staff_fairness[0] ?? {}).map((key) => (
                      <th
                        key={key}
                        className="px-3 py-2 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider capitalize"
                      >
                        {key.replace(/_/g, ' ')}
                      </th>
                    ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {data.staff_fairness.map((row, idx) => (
                  <tr key={idx}>
                    {Object.values(row).map((val, colIdx) => (
                      <td
                        key={colIdx}
                        className="px-3 py-2 text-lsc-dark dark:text-lsc-cream whitespace-nowrap"
                      >
                        {val == null ? '\u2014' : String(val)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AdminShell>
  )
}
