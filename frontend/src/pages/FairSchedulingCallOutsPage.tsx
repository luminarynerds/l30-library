/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Plus, Phone, UserCheck, AlertTriangle, X, Loader2, Users } from 'lucide-react'
import toast from 'react-hot-toast'
import { AdminShell } from '../components/shells/AdminShell'
import { fairSchedulingApi } from '../api/fair-scheduling-api'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Callout {
  id: number
  branch_id: number
  original_shift_id: number
  callout_staff_id: number
  callout_reason: string | null
  callout_time: string
  shift_date: string
  shift_start: string
  shift_end: string
  status: 'open' | 'searching' | 'covered' | 'partial' | 'uncovered' | 'cancelled'
  urgency: 'low' | 'medium' | 'high' | 'emergency'
  staff_contacted: Record<string, unknown>[]
  staff_contacted_count: number
  covering_staff_id: number | null
  resolved_at: string | null
  resolution_notes: string | null
  created_at?: string | null
}

interface Candidate {
  staff_id: number
  name?: string
  score?: number
  reason?: string
}

interface CreateCalloutForm {
  branch_id: number
  original_shift_id: number
  callout_staff_id: number
  callout_reason: string
  urgency: 'low' | 'medium' | 'high' | 'emergency'
}

const URGENCY_BADGE: Record<string, string> = {
  emergency: 'bg-status-danger-600 text-white',
  high: 'bg-status-warning-500 text-white',
  medium: 'bg-status-warning-500 text-white',
  low: 'bg-earth-400 text-white',
}

const STATUS_BADGE: Record<string, string> = {
  open: 'bg-status-info-500 text-white',
  searching: 'bg-status-warning-500 text-white',
  covered: 'bg-lsc-green text-white',
  partial: 'bg-status-warning-500 text-white',
  uncovered: 'bg-status-danger-600 text-white',
  cancelled: 'bg-earth-400 text-white',
}

const INITIAL_FORM: CreateCalloutForm = {
  branch_id: 0,
  original_shift_id: 0,
  callout_staff_id: 0,
  callout_reason: '',
  urgency: 'medium',
}

export default function FairSchedulingCallOutsPage(): React.ReactElement {
  const [callouts, setCallouts] = useState<Callout[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState<CreateCalloutForm>({ ...INITIAL_FORM })

  // Candidates drawer
  const [drawerCalloutId, setDrawerCalloutId] = useState<number | null>(null)
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loadingCandidates, setLoadingCandidates] = useState(false)
  const [assigningId, setAssigningId] = useState<number | null>(null)

  const loadCallouts = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fairSchedulingApi.getOpenCallouts()
      const data = Array.isArray(res) ? res : (res as { data?: Callout[] }).data ?? []
      setCallouts(data)
    } catch {
      toast.error('Failed to load call-outs')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadCallouts()
  }, [loadCallouts])

  const handleCreate = async () => {
    if (!form.branch_id || !form.original_shift_id || !form.callout_staff_id) {
      toast.error('Branch, shift, and staff fields are required')
      return
    }
    setSubmitting(true)
    try {
      await fairSchedulingApi.createCallout({
        branch_id: form.branch_id,
        original_shift_id: form.original_shift_id,
        callout_staff_id: form.callout_staff_id,
        callout_reason: form.callout_reason || '',
        urgency: form.urgency,
      })
      toast.success('Call-out created')
      setShowCreateModal(false)
      setForm({ ...INITIAL_FORM })
      loadCallouts()
    } catch {
      toast.error('Failed to create call-out')
    } finally {
      setSubmitting(false)
    }
  }

  const handleFindCoverage = async (calloutId: number) => {
    setDrawerCalloutId(calloutId)
    setLoadingCandidates(true)
    setCandidates([])
    try {
      const res = await fairSchedulingApi.getCalloutCandidates(calloutId)
      const data = Array.isArray(res) ? res : (res as { data?: Candidate[] }).data ?? []
      setCandidates(data)
    } catch {
      toast.error('Failed to load candidates')
    } finally {
      setLoadingCandidates(false)
    }
  }

  const handleAssign = async (staffId: number) => {
    if (!drawerCalloutId) return
    setAssigningId(staffId)
    try {
      await fairSchedulingApi.assignCallout(drawerCalloutId, { covering_staff_id: staffId })
      toast.success('Coverage assigned')
      setDrawerCalloutId(null)
      setCandidates([])
      loadCallouts()
    } catch {
      toast.error('Failed to assign coverage')
    } finally {
      setAssigningId(null)
    }
  }

  const closeDrawer = () => {
    setDrawerCalloutId(null)
    setCandidates([])
  }

  const formatTime = (t: string) => {
    if (!t) return ''
    const [h = '0', m = '00'] = t.split(':')
    const hr = parseInt(h, 10)
    const ampm = hr >= 12 ? 'PM' : 'AM'
    return `${hr % 12 || 12}:${m} ${ampm}`
  }

  return (
    <AdminShell title="Call-Out Coverage" subtitle="Manage call-outs and find coverage">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream">
          <Phone className="h-5 w-5" />
          <span className="text-lg font-semibold">
            {callouts.length} Open Call-Out{callouts.length !== 1 ? 's' : ''}
          </span>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Call-Out
        </button>
      </div>

      {/* Call-outs table */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
          </div>
        ) : callouts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-lsc-dark/70 dark:text-lsc-cream/70">
            <AlertTriangle className="h-8 w-8 mb-2" />
            <p>No open call-outs</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-lsc-dark dark:text-lsc-cream">
              <thead>
                <tr className="border-b border-lsc-border dark:border-earth-700 text-left text-lsc-dark/70 dark:text-lsc-cream/70">
                  <th className="px-4 py-3 font-medium">ID</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Shift Time</th>
                  <th className="px-4 py-3 font-medium">Urgency</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Staff ID</th>
                  <th className="px-4 py-3 font-medium">Reason</th>
                  <th className="px-4 py-3 font-medium">Contacted</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {callouts.map((c) => (
                  <tr key={c.id} className="border-b border-lsc-border dark:border-earth-700 last:border-b-0 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                    <td className="px-4 py-3 font-mono text-xs">{c.id}</td>
                    <td className="px-4 py-3">{c.shift_date}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {formatTime(c.shift_start)} - {formatTime(c.shift_end)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${URGENCY_BADGE[c.urgency] ?? ''}`}>
                        {c.urgency}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATUS_BADGE[c.status] ?? ''}`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">{c.callout_staff_id}</td>
                    <td className="px-4 py-3 max-w-[200px] truncate">{c.callout_reason ?? '-'}</td>
                    <td className="px-4 py-3 text-center">{c.staff_contacted_count}</td>
                    <td className="px-4 py-3">
                      {(c.status === 'open' || c.status === 'searching') && (
                        <button
                          onClick={() => handleFindCoverage(c.id)}
                          className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors"
                        >
                          <Users className="h-3.5 w-3.5" />
                          Find Coverage
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

      {/* Create Call-Out Modal */}
      {showCreateModal && (
        <ModalBackdrop onClose={handleCreate} title="New Call-Out">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 w-full max-w-md mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                New Call-Out
              </h2>
              <button
                onClick={() => { setShowCreateModal(false); setForm({ ...INITIAL_FORM }) }}
                className="p-1 text-lsc-dark/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Branch ID
                </label>
                <input
                  type="number"
                  value={form.branch_id || ''}
                  onChange={(e) => setForm({ ...form, branch_id: parseInt(e.target.value, 10) || 0 })}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  placeholder="1"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Original Shift ID
                </label>
                <input
                  type="number"
                  value={form.original_shift_id || ''}
                  onChange={(e) => setForm({ ...form, original_shift_id: parseInt(e.target.value, 10) || 0 })}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  placeholder="Shift to cover"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Call-Out Staff ID
                </label>
                <input
                  type="number"
                  value={form.callout_staff_id || ''}
                  onChange={(e) => setForm({ ...form, callout_staff_id: parseInt(e.target.value, 10) || 0 })}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  placeholder="Staff member calling out"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Reason
                </label>
                <input
                  type="text"
                  value={form.callout_reason}
                  onChange={(e) => setForm({ ...form, callout_reason: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  placeholder="Optional reason"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Urgency
                </label>
                <select
                  value={form.urgency}
                  onChange={(e) => setForm({ ...form, urgency: e.target.value as CreateCalloutForm['urgency'] })}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="emergency">Emergency</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => { setShowCreateModal(false); setForm({ ...INITIAL_FORM }) }}
                className="px-4 py-2 text-sm font-medium text-lsc-dark/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={submitting}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {submitting && <Loader2 className="h-4 w-4 motion-safe:animate-spin" />}
                Create Call-Out
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}

      {/* Candidates Drawer */}
      {drawerCalloutId !== null && (
        <ModalBackdrop onClose={closeDrawer} title="Coverage Candidates">
          <div className="bg-lsc-white dark:bg-earth-800 border-l border-lsc-border dark:border-earth-700 w-full max-w-md h-full overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                  Coverage Candidates
                </h2>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Call-out #{drawerCalloutId}
                </p>
              </div>
              <button
                onClick={closeDrawer}
                className="p-1 text-lsc-dark/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {loadingCandidates ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
              </div>
            ) : candidates.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-lsc-dark/70 dark:text-lsc-cream/70">
                <Users className="h-8 w-8 mb-2" />
                <p>No candidates available</p>
              </div>
            ) : (
              <div className="space-y-3">
                {candidates.map((c) => (
                  <div
                    key={c.staff_id}
                    className="flex items-center justify-between p-4 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800"
                  >
                    <div>
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {c.name ?? `Staff #${c.staff_id}`}
                      </p>
                      {c.score !== undefined && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          Score: {c.score}
                        </p>
                      )}
                      {c.reason && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                          {c.reason}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => handleAssign(c.staff_id)}
                      disabled={assigningId === c.staff_id}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors disabled:opacity-50"
                    >
                      {assigningId === c.staff_id ? (
                        <Loader2 className="h-3.5 w-3.5 motion-safe:animate-spin" />
                      ) : (
                        <UserCheck className="h-3.5 w-3.5" />
                      )}
                      Assign
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </ModalBackdrop>
      )}
    </AdminShell>
  )
}
