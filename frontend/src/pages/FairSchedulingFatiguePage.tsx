/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { AdminShell } from '../components/shells/AdminShell'
import { fairSchedulingApi } from '../api/fair-scheduling-api'
import { useBranchOptions } from '@/hooks/useBranchOptions'
import { AlertTriangle, Activity, Clock, TrendingUp, TrendingDown, Loader2 } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import toast from 'react-hot-toast'

interface FatigueRecord {
  id: number
  staff_id: number
  record_date: string
  fatigue_level: 'low' | 'moderate' | 'high' | 'critical'
  fatigue_score: number
  consecutive_days_worked: number
  hours_last_7_days: number
  hours_last_14_days: number
  closing_shifts_last_7_days: number
  short_turnarounds_last_14_days: number
  overtime_hours_last_30_days: number
  days_since_last_day_off: number
  weekend_shifts_last_30_days: number
  fatigue_trend: string | null
  alert_triggered: boolean
  alert_message: string | null
  calculated_at: string
}

const FATIGUE_BADGE: Record<FatigueRecord['fatigue_level'], string> = {
  critical: 'bg-status-danger-600 text-white',
  high: 'bg-status-warning-500 text-white',
  moderate: 'bg-status-warning-500 text-white',
  low: 'bg-lsc-green text-white',
}

export default function FairSchedulingFatiguePage(): React.ReactElement {

  const [branchId, setBranchId] = useState(1)
  const { branches, loading: branchesLoading } = useBranchOptions()

  useEffect(() => {
    if (branches.length > 0 && !branches.some((b) => b.id === branchId)) {
      setBranchId(branches[0]!.id)
    }
  }, [branches, branchId])
  const [loading, setLoading] = useState(false)
  const [teamRecords, setTeamRecords] = useState<FatigueRecord[]>([])

  const [selectedStaffId, setSelectedStaffId] = useState<number | null>(null)
  const [staffDetail, setStaffDetail] = useState<FatigueRecord | null>(null)
  const [staffHistory, setStaffHistory] = useState<FatigueRecord[]>([])
  const [detailLoading, setDetailLoading] = useState(false)

  const loadTeamFatigue = async () => {
    setLoading(true)
    setSelectedStaffId(null)
    setStaffDetail(null)
    setStaffHistory([])
    try {
      const res = await fairSchedulingApi.getTeamFatigue(branchId)
      const data = Array.isArray(res) ? res : res.data ?? res.items ?? []
      setTeamRecords(data)
    } catch (_err) {
      toast.error('Failed to load team fatigue data')
    } finally {
      setLoading(false)
    }
  }

  const loadStaffDetail = async (staffId: number) => {
    setSelectedStaffId(staffId)
    setDetailLoading(true)
    try {
      const [currentRes, historyRes] = await Promise.all([
        fairSchedulingApi.getStaffFatigue(staffId),
        fairSchedulingApi.getStaffFatigueHistory(staffId),
      ])
      const current = currentRes.data ?? currentRes
      const history = Array.isArray(historyRes) ? historyRes : historyRes.data ?? historyRes.items ?? []
      setStaffDetail(Array.isArray(current) ? current[0] ?? null : current)
      setStaffHistory(history)
    } catch (_err) {
      toast.error('Failed to load staff fatigue details')
    } finally {
      setDetailLoading(false)
    }
  }

  const alerts = teamRecords.filter(
    (r) => r.alert_triggered || r.fatigue_level === 'critical' || r.fatigue_level === 'high'
  )

  const trendIcon = (trend: string | null) => {
    if (!trend) return null
    if (trend.toLowerCase().includes('up') || trend.toLowerCase().includes('increas'))
      return <TrendingUp className="h-4 w-4 text-status-danger-500 inline ml-1" />
    if (trend.toLowerCase().includes('down') || trend.toLowerCase().includes('decreas'))
      return <TrendingDown className="h-4 w-4 text-lsc-green inline ml-1" />
    return null
  }

  return (
    <AdminShell title="Fatigue Monitoring" subtitle="Track staff fatigue and workload">
      <div className="space-y-6">
        {/* Branch Selector */}
        <div className="flex items-center gap-3">
          <label htmlFor="fatigue-branch" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Branch</label>
          <select
            id="fatigue-branch"
            value={branchId}
            onChange={(e) => setBranchId(Number(e.target.value))}
            disabled={branchesLoading}
            className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
          >
            {branchesLoading && <option value={branchId}>Loading branches...</option>}
            {branches.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
          <button
            onClick={loadTeamFatigue}
            disabled={loading}
            className="bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            {loading && <Loader2 className="h-4 w-4 motion-safe:animate-spin" />}
            Load
          </button>
        </div>

        {/* Alerts */}
        {alerts.length > 0 && (
          <div className="border-l-4 border-status-danger-600 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-xl p-4 space-y-2">
            <div className="flex items-center gap-2 text-status-danger-700 dark:text-status-danger-400 font-semibold text-sm">
              <AlertTriangle className="h-5 w-5" />
              Fatigue Alerts ({alerts.length})
            </div>
            {alerts.map((a) => (
              <div key={a.id} className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 pl-7">
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">Staff #{a.staff_id}</span>
                {' - '}
                <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${FATIGUE_BADGE[a.fatigue_level]}`}>
                  {a.fatigue_level}
                </span>
                {a.alert_message && <span className="ml-2">{a.alert_message}</span>}
              </div>
            ))}
          </div>
        )}

        {/* Team Grid */}
        {teamRecords.length > 0 && (
          <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
              <h2 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Team Fatigue Overview
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-lsc-border dark:border-earth-700 text-left text-lsc-dark/70 dark:text-lsc-cream/70">
                    <th className="px-4 py-2 font-medium">Staff ID</th>
                    <th className="px-4 py-2 font-medium">Level</th>
                    <th className="px-4 py-2 font-medium">Score</th>
                    <th className="px-4 py-2 font-medium">Trend</th>
                    <th className="px-4 py-2 font-medium">Consec. Days</th>
                    <th className="px-4 py-2 font-medium">Hours (7d)</th>
                    <th className="px-4 py-2 font-medium">Days Off</th>
                  </tr>
                </thead>
                <tbody>
                  {teamRecords.map((r) => (
                    <tr
                      key={r.id}
                      className={`border-b border-lsc-border dark:border-earth-700 transition-colors ${
                        selectedStaffId === r.staff_id ? 'bg-lsc-cream/70 dark:bg-earth-700/70' : ''
                      }`}
                    >
                      <td className="px-4 py-2 font-medium">
                        <button
                          type="button"
                          onClick={() => loadStaffDetail(r.staff_id)}
                          aria-pressed={selectedStaffId === r.staff_id}
                          aria-label={`View fatigue details for staff #${r.staff_id}`}
                          className="text-lsc-rose hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded px-1 -mx-1"
                        >
                          #{r.staff_id}
                        </button>
                      </td>
                      <td className="px-4 py-2">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${FATIGUE_BADGE[r.fatigue_level]}`}>
                          {r.fatigue_level}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-lsc-dark dark:text-lsc-cream">{r.fatigue_score}</td>
                      <td className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                        {r.fatigue_trend ?? '--'}
                        {trendIcon(r.fatigue_trend)}
                      </td>
                      <td className="px-4 py-2 text-lsc-dark dark:text-lsc-cream">{r.consecutive_days_worked}</td>
                      <td className="px-4 py-2 text-lsc-dark dark:text-lsc-cream">{r.hours_last_7_days}</td>
                      <td className="px-4 py-2 text-lsc-dark dark:text-lsc-cream">{r.days_since_last_day_off}d ago</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!loading && teamRecords.length === 0 && (
          <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
            Choose a branch and click Load to view fatigue data.
          </div>
        )}

        {/* Staff Detail */}
        {selectedStaffId !== null && (
          <div className="space-y-4">
            {detailLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : (
              <>
                {staffHistory.length > 0 && (
                  <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
                    <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
                      <Activity className="h-4 w-4" />
                      Fatigue History - Staff #{selectedStaffId}
                    </h3>
                    <ResponsiveContainer width="100%" height={280}>
                      <LineChart data={staffHistory.map((h) => ({ date: h.record_date, score: h.fatigue_score }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={(v: string) => v.slice(5)} />
                        <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
                        <Tooltip />
                        <Line type="monotone" dataKey="score" stroke="#e87434" strokeWidth={2} dot={{ r: 3 }} name="Fatigue Score" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {staffDetail && (
                  <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Current Fatigue Breakdown - Staff #{staffDetail.staff_id}
                      </h3>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${FATIGUE_BADGE[staffDetail.fatigue_level]}`}>
                        {staffDetail.fatigue_level} ({staffDetail.fatigue_score}/100)
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                      <DetailStat icon={<Clock className="h-4 w-4" />} label="Consecutive Days Worked" value={staffDetail.consecutive_days_worked} />
                      <DetailStat icon={<Clock className="h-4 w-4" />} label="Hours Last 7 Days" value={staffDetail.hours_last_7_days} />
                      <DetailStat icon={<Clock className="h-4 w-4" />} label="Hours Last 14 Days" value={staffDetail.hours_last_14_days} />
                      <DetailStat icon={<Clock className="h-4 w-4" />} label="Days Since Last Day Off" value={staffDetail.days_since_last_day_off} />
                      <DetailStat icon={<Activity className="h-4 w-4" />} label="Closing Shifts (7d)" value={staffDetail.closing_shifts_last_7_days} />
                      <DetailStat icon={<AlertTriangle className="h-4 w-4" />} label="Short Turnarounds (14d)" value={staffDetail.short_turnarounds_last_14_days} />
                      <DetailStat icon={<Clock className="h-4 w-4" />} label="Overtime Hours (30d)" value={staffDetail.overtime_hours_last_30_days} />
                      <DetailStat icon={<Activity className="h-4 w-4" />} label="Weekend Shifts (30d)" value={staffDetail.weekend_shifts_last_30_days} />
                    </div>
                    {staffDetail.alert_message && (
                      <div className="mt-4 border-l-4 border-status-danger-600 bg-status-danger-50 dark:bg-status-danger-900/20 rounded p-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        <AlertTriangle className="h-4 w-4 inline mr-1 text-status-danger-600" />
                        {staffDetail.alert_message}
                      </div>
                    )}
                    <div className="mt-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      Calculated at: {new Date(staffDetail.calculated_at).toLocaleString()}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </AdminShell>
  )
}

function DetailStat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs">
        {icon}
        {label}
      </div>
      <div className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{value}</div>
    </div>
  )
}
