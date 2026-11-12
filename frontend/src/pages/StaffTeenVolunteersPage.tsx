/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { AdminShell } from '../components/shells/AdminShell'
import { Users, Loader2, CheckCircle, Clock, GraduationCap, Award, AlertCircle, UserCheck, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../api/api'

interface TeenVolunteer {
  id: number
  first_name: string
  last_name: string
  email: string
  status: string
  school_name: string | null
  grade_level: string | null
  guardian_name: string
  total_service_hours: number
  total_tasks_completed: number
  date_of_birth: string | null
  is_teen_board_member: boolean
  current_recognition_level: string
  created_at: string | null
}

interface Stats {
  total: number
  active: number
  pending: number
  total_hours: number
}

interface BoardMember {
  id: number
  first_name: string
  last_name: string
  position: string | null
  term_start: string | null
  term_end: string | null
  total_meetings_attended: number
  total_meetings_held: number
  attendance_percentage: number
  is_active: boolean
  initiatives_proposed: number
  initiatives_approved: number
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending_approval: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    active: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
    inactive: 'bg-lsc-cream text-lsc-dark/70 dark:bg-earth-700/30 dark:text-lsc-cream/70',
    on_leave: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
    suspended: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    completed: 'bg-earth-100 text-earth-700 dark:bg-earth-800/30 dark:text-earth-300',
  }
  const labels: Record<string, string> = {
    pending_approval: 'Pending',
    active: 'Active',
    inactive: 'Inactive',
    on_leave: 'On Leave',
    suspended: 'Suspended',
    completed: 'Completed',
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status] || styles.inactive}`}>
      {labels[status] || status}
    </span>
  )
}

export default function StaffTeenVolunteersPage(): React.ReactElement {
  const [volunteers, setVolunteers] = useState<TeenVolunteer[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [board, setBoard] = useState<BoardMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [approving, setApproving] = useState<number | null>(null)
  const [statusFilter, setStatusFilter] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = statusFilter ? `?status_filter=${statusFilter}` : ''
      const [vols, st, bd] = await Promise.all([
        api.get(`/teen-volunteers${params}`),
        api.get('/teen-volunteers/stats'),
        api.get('/teen-volunteers/advisory-board'),
      ])
      setVolunteers(Array.isArray(vols) ? vols : [])
      setStats(st)
      setBoard(Array.isArray(bd) ? bd : [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => { fetchData() }, [fetchData])

  const handleApprove = async (id: number) => {
    setApproving(id)
    try {
      await api.post(`/teen-volunteers/${id}/approve`)
      toast.success('Teen volunteer approved')
      await fetchData()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to approve')
    } finally {
      setApproving(null)
    }
  }

  return (
    <AdminShell title="Teen Volunteers">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <GraduationCap className="w-6 h-6 text-lsc-rose" />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Teen Volunteer Program</h1>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Manage teen volunteer enrollment and service hours</p>
            </div>
          </div>
          <button onClick={fetchData} aria-label="Refresh data" className="p-2 rounded-lg bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-200 dark:hover:bg-earth-600 transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Volunteers', value: stats.total, icon: Users, color: 'bg-earth-600' },
              { label: 'Active', value: stats.active, icon: CheckCircle, color: 'bg-status-success-600' },
              { label: 'Pending Approval', value: stats.pending, icon: AlertCircle, color: 'bg-lsc-rose' },
              { label: 'Total Service Hours', value: stats.total_hours.toFixed(1), icon: Clock, color: 'bg-earth-500' },
            ].map(stat => (
              <div key={stat.label} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg ${stat.color} flex items-center justify-center`}>
                    <stat.icon className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stat.value}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{stat.label}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 text-status-danger-700 dark:text-status-danger-400 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Filter */}
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-1.5 text-sm"
          >
            <option value="">All</option>
            <option value="pending_approval">Pending</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="on_leave">On Leave</option>
            <option value="suspended">Suspended</option>
            <option value="completed">Completed</option>
          </select>
        </div>

        {/* Volunteers Table */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden border border-lsc-border dark:border-earth-700">
          <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <GraduationCap className="w-5 h-5" /> Volunteers
            </h2>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
            </div>
          ) : volunteers.length === 0 ? (
            <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No teen volunteers found.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-lsc-cream/50 dark:bg-earth-700/50 text-left">
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Name</th>
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">School</th>
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Grade</th>
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Guardian</th>
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 text-right">Hours</th>
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 text-right">Tasks</th>
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {volunteers.map((v) => (
                    <tr key={v.id} className="hover:bg-lsc-cream/20 dark:hover:bg-earth-700/20 transition-colors">
                      <td className="px-4 py-3 text-lsc-dark dark:text-lsc-cream font-medium">{v.first_name} {v.last_name}</td>
                      <td className="px-4 py-3"><StatusBadge status={v.status} /></td>
                      <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{v.school_name || '--'}</td>
                      <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{v.grade_level || '--'}</td>
                      <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{v.guardian_name}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-lsc-dark/70 dark:text-lsc-cream/70">{v.total_service_hours}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-lsc-dark/70 dark:text-lsc-cream/70">{v.total_tasks_completed}</td>
                      <td className="px-4 py-3">
                        {v.status === 'pending_approval' && (
                          <button
                            onClick={() => handleApprove(v.id)}
                            disabled={approving === v.id}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-status-success-600 hover:bg-status-success-700 text-white text-xs font-medium transition-colors disabled:opacity-50"
                          >
                            {approving === v.id ? <Loader2 className="w-3 h-3 motion-safe:animate-spin" /> : <UserCheck className="w-3 h-3" />}
                            Approve
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Advisory Board */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden border border-lsc-border dark:border-earth-700">
          <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Award className="w-5 h-5 text-lsc-rose" /> Teen Advisory Board
            </h2>
          </div>
          {board.length === 0 ? (
            <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">No advisory board members.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-lsc-cream/50 dark:bg-earth-700/50 text-left">
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Member</th>
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Position</th>
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Term</th>
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 text-right">Attendance</th>
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 text-right">Initiatives</th>
                    <th className="px-4 py-3 font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {board.map((m) => (
                    <tr key={m.id} className="hover:bg-lsc-cream/20 dark:hover:bg-earth-700/20 transition-colors">
                      <td className="px-4 py-3 text-lsc-dark dark:text-lsc-cream font-medium">{m.first_name} {m.last_name}</td>
                      <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{m.position || 'Member'}</td>
                      <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{m.term_start || '--'} to {m.term_end || 'Present'}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-lsc-dark/70 dark:text-lsc-cream/70">
                        {m.total_meetings_attended}/{m.total_meetings_held} ({m.attendance_percentage.toFixed(0)}%)
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-lsc-dark/70 dark:text-lsc-cream/70">
                        {m.initiatives_proposed} proposed, {m.initiatives_approved} approved
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          m.is_active
                            ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400'
                            : 'bg-lsc-cream text-lsc-dark/70 dark:bg-earth-700/30 dark:text-lsc-cream/70'
                        }`}>
                          {m.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AdminShell>
  )
}
