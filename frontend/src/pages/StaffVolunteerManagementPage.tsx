/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AdminShell } from '../components/shells/AdminShell'
import { volunteerApi } from '@/api/domains/admin/volunteer-api'
import { ROLE_CATEGORY_LABELS, HOUR_LOG_STATUS_LABELS } from '@/api/domains/admin/volunteer-api'
import type { StaffShift, ShiftCreateData, ShiftUpdateData, PendingHourLog } from '@/api/domains/admin/volunteer-api'
import ConfirmDialog from '@/components/ConfirmDialog'
import { ShiftFormModal } from '@/components/volunteers/ShiftFormModal'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { formatDate } from '@/utils/format-utils'
import toast from 'react-hot-toast'
import {
  Users,
  Clock,
  ClipboardList,
  ClipboardCheck,
  CheckCircle,
  XCircle,
  Loader2,
  UserCheck,
  Calendar,
  Plus,
  Pencil,
  Ban,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'

interface ApplicationItem {
  id: number
  user_id: number
  first_name: string | null
  last_name: string | null
  email: string | null
  status: string
  submitted_at: string | null
  preferred_roles: string[]
  why_volunteer: string
  availability_hours_per_week: number
}

interface RosterItem {
  id: number
  user_id: number
  first_name: string | null
  last_name: string | null
  email: string | null
  status: string
  primary_role_category: string
  total_hours: number
  total_shifts: number
  last_active_at: string | null
  start_date: string | null
}

interface ProgramOverview {
  active_volunteers: number
  pending_applications: number
  total_hours_this_month: number
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}: {
  title: string
  value: number | string
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{title}</p>
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
    pending_background: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    pending_training: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-400',
    inactive: 'bg-lsc-cream text-lsc-dark/70 dark:bg-earth-800/30 dark:text-lsc-cream/70',
    on_leave: 'bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300',
    suspended: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    terminated: 'bg-status-danger-200 text-status-danger-900 dark:bg-status-danger-900/50 dark:text-status-danger-300',
  }
  const label = status.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status] || styles.inactive}`}>
      {label}
    </span>
  )
}

function PaginationControls({
  page,
  total,
  limit,
  onPageChange,
}: {
  page: number
  total: number
  limit: number
  onPageChange: (page: number) => void
}) {
  if (total <= limit) return null

  const totalPages = Math.ceil(total / limit)

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-lsc-border dark:border-earth-700">
      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        Page {page} of {totalPages}
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page === 1}
          aria-label="Previous page"
          className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <button
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page === totalPages}
          aria-label="Next page"
          className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}

function ApplicationsTab() {
  const queryClient = useQueryClient()
  const [approveTarget, setApproveTarget] = useState<ApplicationItem | null>(null)
  const [rejectTarget, setRejectTarget] = useState<ApplicationItem | null>(null)
  const [rejectReason, setRejectReason] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['volunteer-applications', 'pending'],
    queryFn: () => volunteerApi.listApplications('submitted'),
  })

  const approveMut = useMutation({
    mutationFn: (id: number) => volunteerApi.reviewApplication(id, 'approved'),
    onSuccess: () => {
      toast.success('Application approved')
      queryClient.invalidateQueries({ queryKey: ['volunteer-applications'] })
      queryClient.invalidateQueries({ queryKey: ['volunteer-overview'] })
      queryClient.invalidateQueries({ queryKey: ['volunteer-roster'] })
      setApproveTarget(null)
    },
    onError: () => toast.error('Failed to approve application'),
  })

  const rejectMut = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      volunteerApi.reviewApplication(id, 'denied', reason),
    onSuccess: () => {
      toast.success('Application rejected')
      queryClient.invalidateQueries({ queryKey: ['volunteer-applications'] })
      queryClient.invalidateQueries({ queryKey: ['volunteer-overview'] })
      setRejectTarget(null)
      setRejectReason('')
    },
    onError: () => toast.error('Failed to reject application'),
  })

  const applications: ApplicationItem[] = data?.applications ?? []

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (applications.length === 0) {
    return (
      <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
        <ClipboardList className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p className="font-medium">No pending applications</p>
        <p className="text-sm mt-1">New applications will appear here when submitted.</p>
      </div>
    )
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-lsc-border dark:border-earth-700">
              <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Name</th>
              <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Email</th>
              <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Interests</th>
              <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Submitted</th>
              <th className="text-right py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Actions</th>
            </tr>
          </thead>
          <tbody>
            {applications.map((app) => (
              <tr key={app.id} className="border-b border-lsc-border/50 dark:border-earth-700/50 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                <td className="py-3 px-4 text-lsc-dark dark:text-lsc-cream font-medium">
                  {app.first_name} {app.last_name}
                </td>
                <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70">
                  {app.email}
                </td>
                <td className="py-3 px-4">
                  <div className="flex flex-wrap gap-1">
                    {(app.preferred_roles ?? []).map((role) => (
                      <span
                        key={role}
                        className="inline-block px-2 py-0.5 text-xs rounded-full bg-earth-100 text-earth-700 dark:bg-earth-700 dark:text-earth-200"
                      >
                        {role.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">
                  {app.submitted_at
                    ? new Date(app.submitted_at).toLocaleDateString()
                    : '---'}
                </td>
                <td className="py-3 px-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => setApproveTarget(app)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-status-success-600 text-white hover:bg-status-success-700 transition-colors"
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      Approve
                    </button>
                    <button
                      onClick={() => setRejectTarget(app)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-status-danger-600 text-white hover:bg-status-danger-700 transition-colors"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Reject
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        isOpen={!!approveTarget}
        title="Approve Volunteer Application"
        message={
          approveTarget ? (
            <div className="space-y-2">
              <p>
                Approve <strong>{approveTarget.first_name} {approveTarget.last_name}</strong> as
                a volunteer?
              </p>
              {approveTarget.why_volunteer && (
                <div className="p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg text-sm">
                  <p className="font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Why they want to volunteer:</p>
                  <p className="text-lsc-dark dark:text-lsc-cream">{approveTarget.why_volunteer}</p>
                </div>
              )}
            </div>
          ) : ''
        }
        confirmText="Approve"
        confirmVariant="success"
        onConfirm={() => { if (approveTarget) approveMut.mutate(approveTarget.id) }}
        onCancel={() => setApproveTarget(null)}
        loading={approveMut.isPending}
      />

      <ConfirmDialog
        isOpen={!!rejectTarget}
        title="Reject Volunteer Application"
        message={
          rejectTarget ? (
            <div className="space-y-3">
              <p>
                Reject the application from <strong>{rejectTarget.first_name} {rejectTarget.last_name}</strong>?
              </p>
              <div>
                <label htmlFor="application-reject-reason" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Reason for rejection
                </label>
                <textarea
                  id="application-reject-reason"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  rows={3}
                  disabled={rejectMut.isPending}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent disabled:opacity-50"
                  placeholder="Provide a reason for the rejection..."
                />
              </div>
            </div>
          ) : ''
        }
        confirmText="Reject Application"
        confirmVariant="danger"
        confirmDisabled={rejectReason.trim() === ''}
        onConfirm={() =>
          { if (rejectTarget) rejectMut.mutate({ id: rejectTarget.id, reason: rejectReason.trim() }) }
        }
        onCancel={() => {
          setRejectTarget(null)
          setRejectReason('')
        }}
        loading={rejectMut.isPending}
      />
    </>
  )
}

function RosterTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['volunteer-roster'],
    queryFn: () => volunteerApi.getRoster(),
  })

  const volunteers: RosterItem[] = data?.volunteers ?? []

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (volunteers.length === 0) {
    return (
      <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
        <Users className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p className="font-medium">No volunteers yet</p>
        <p className="text-sm mt-1">Approved volunteers will appear here.</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-lsc-border dark:border-earth-700">
            <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Name</th>
            <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Role</th>
            <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
            <th className="text-right py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Total Hours</th>
            <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Last Active</th>
          </tr>
        </thead>
        <tbody>
          {volunteers.map((v) => (
            <tr key={v.id} className="border-b border-lsc-border/50 dark:border-earth-700/50 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
              <td className="py-3 px-4">
                <div>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                    {v.first_name} {v.last_name}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{v.email}</p>
                </div>
              </td>
              <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                {(v.primary_role_category ?? '').replace(/_/g, ' ')}
              </td>
              <td className="py-3 px-4">
                <StatusBadge status={v.status} />
              </td>
              <td className="py-3 px-4 text-right text-lsc-dark dark:text-lsc-cream tabular-nums">
                {v.total_hours.toFixed(1)}
              </td>
              <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">
                {v.last_active_at
                  ? new Date(v.last_active_at).toLocaleDateString()
                  : 'Never'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ShiftsTab() {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [editTarget, setEditTarget] = useState<StaffShift | null>(null)
  const [cancelTarget, setCancelTarget] = useState<StaffShift | null>(null)
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['volunteer-shifts-staff', page],
    queryFn: () => volunteerApi.listShiftsStaff({ includeCancelled: true, page }),
  })

  const invalidateShifts = () => queryClient.invalidateQueries({ queryKey: ['volunteer-shifts-staff'] })

  const createMut = useMutation({
    mutationFn: (payload: ShiftCreateData) => volunteerApi.createShift(payload),
    onSuccess: () => {
      toast.success('Shift created')
      invalidateShifts()
      setShowCreate(false)
    },
    onError: () => toast.error('Failed to create shift'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, updates }: { id: number; updates: ShiftUpdateData }) =>
      volunteerApi.updateShift(id, updates),
    onSuccess: () => {
      toast.success('Shift updated')
      invalidateShifts()
      setEditTarget(null)
    },
    onError: () => toast.error('Failed to update shift'),
  })

  const cancelMut = useMutation({
    mutationFn: (id: number) => volunteerApi.cancelShift(id),
    onSuccess: () => {
      toast.success('Shift cancelled')
      invalidateShifts()
      setCancelTarget(null)
    },
    onError: () => toast.error('Failed to cancel shift'),
  })

  const shifts: StaffShift[] = data?.shifts ?? []
  const total: number = data?.total ?? shifts.length
  const limit: number = data?.limit ?? shifts.length

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  return (
    <>
      <div className="flex justify-end p-4 border-b border-lsc-border dark:border-earth-700">
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          New Shift
        </button>
      </div>

      {shifts.length === 0 ? (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
          <Calendar className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="font-medium">No shifts yet</p>
          <p className="text-sm mt-1">Create a shift to open it up for volunteer sign-up.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-lsc-border dark:border-earth-700">
                <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Shift</th>
                <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Role</th>
                <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Date</th>
                <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Time</th>
                <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Spots</th>
                <th className="text-right py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Actions</th>
              </tr>
            </thead>
            <tbody>
              {shifts.map((shift) => (
                <tr key={shift.id} className="border-b border-lsc-border/50 dark:border-earth-700/50 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                  <td className="py-3 px-4 text-lsc-dark dark:text-lsc-cream font-medium">
                    <div className="flex items-center gap-2">
                      {shift.title}
                      {shift.cancelled && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400">
                          Cancelled
                        </span>
                      )}
                    </div>
                    {shift.location && (
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{shift.location}</p>
                    )}
                  </td>
                  <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70">
                    {ROLE_CATEGORY_LABELS[shift.role_category] ?? shift.role_category}
                  </td>
                  <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">
                    {formatDate(shift.shift_date)}
                  </td>
                  <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">
                    {shift.start_time}&ndash;{shift.end_time}
                  </td>
                  <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70 tabular-nums">
                    {shift.volunteers_signed_up}/{shift.volunteers_needed}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setEditTarget(shift)}
                        aria-label={`Edit ${shift.title}`}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-earth-600 transition-colors"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                        Edit
                      </button>
                      {!shift.cancelled && (
                        <button
                          onClick={() => setCancelTarget(shift)}
                          aria-label={`Cancel ${shift.title}`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-status-danger-600 text-white hover:bg-status-danger-700 transition-colors"
                        >
                          <Ban className="w-3.5 h-3.5" />
                          Cancel
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <PaginationControls page={page} total={total} limit={limit} onPageChange={setPage} />
        </div>
      )}

      {showCreate && (
        <ShiftFormModal<ShiftCreateData>
          onClose={() => setShowCreate(false)}
          onSave={(data) => createMut.mutate(data)}
          saving={createMut.isPending}
        />
      )}

      {editTarget && (
        <ShiftFormModal<ShiftUpdateData>
          onClose={() => setEditTarget(null)}
          onSave={(data) => updateMut.mutate({ id: editTarget.id, updates: data })}
          saving={updateMut.isPending}
          initial={editTarget}
        />
      )}

      <ConfirmDialog
        isOpen={!!cancelTarget}
        title="Cancel Shift"
        message={
          cancelTarget ? (
            <>
              Cancel <strong>{cancelTarget.title}</strong> on{' '}
              {formatDate(cancelTarget.shift_date)}? Existing sign-ups and
              hour history are kept -- this just takes the shift off the open sign-up list.
            </>
          ) : ''
        }
        confirmText="Cancel Shift"
        confirmVariant="danger"
        onConfirm={() => { if (cancelTarget) cancelMut.mutate(cancelTarget.id) }}
        onCancel={() => setCancelTarget(null)}
        loading={cancelMut.isPending}
      />
    </>
  )
}

function HourLogsTab() {
  const queryClient = useQueryClient()
  const [verifyTarget, setVerifyTarget] = useState<PendingHourLog | null>(null)
  const [rejectTarget, setRejectTarget] = useState<PendingHourLog | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['volunteer-hour-logs', 'submitted', page],
    queryFn: () => volunteerApi.listPendingHourLogs('submitted', { page }),
  })

  const invalidateHourLogs = () => {
    queryClient.invalidateQueries({ queryKey: ['volunteer-hour-logs'] })
    queryClient.invalidateQueries({ queryKey: ['volunteer-roster'] })
    queryClient.invalidateQueries({ queryKey: ['volunteer-overview'] })
  }

  const verifyMut = useMutation({
    mutationFn: (id: number) => volunteerApi.verifyHours(id),
    onSuccess: () => {
      toast.success('Hours verified')
      invalidateHourLogs()
      setVerifyTarget(null)
    },
    onError: () => toast.error('Failed to verify hours'),
  })

  const rejectMut = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      volunteerApi.rejectHours(id, reason),
    onSuccess: () => {
      toast.success('Hours rejected')
      invalidateHourLogs()
      setRejectTarget(null)
      setRejectReason('')
    },
    onError: () => toast.error('Failed to reject hours'),
  })

  const logs: PendingHourLog[] = data?.hour_logs ?? []
  const total: number = data?.total ?? logs.length
  const limit: number = data?.limit ?? logs.length

  // Verify/reject shrinks the queue out from under a paged-in view: clearing
  // the last item on page 2+ would otherwise refetch to an empty page and
  // strand staff behind the "no hours pending" empty state with 50 real
  // items sitting on page 1 and no way back. Step back one page instead.
  useEffect(() => {
    if (!isLoading && logs.length === 0 && page > 1) {
      setPage((p) => Math.max(1, p - 1))
    }
  }, [isLoading, logs.length, page])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (logs.length === 0) {
    return (
      <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
        <ClipboardCheck className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p className="font-medium">No hours awaiting verification</p>
        <p className="text-sm mt-1">Submitted hour logs will appear here for review.</p>
      </div>
    )
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-lsc-border dark:border-earth-700">
              <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Volunteer</th>
              <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Date</th>
              <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Activity</th>
              <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Description</th>
              <th className="text-right py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Hours</th>
              <th className="text-left py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
              <th className="text-right py-3 px-4 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Actions</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className="border-b border-lsc-border/50 dark:border-earth-700/50 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                <td className="py-3 px-4 text-lsc-dark dark:text-lsc-cream font-medium">
                  {log.volunteer_name || `Volunteer #${log.volunteer_id}`}
                </td>
                <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">
                  {formatDate(log.log_date)}
                </td>
                <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                  {log.activity_type.replace(/_/g, ' ')}
                </td>
                <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70">
                  {log.description || '---'}
                </td>
                <td className="py-3 px-4 text-right text-lsc-dark dark:text-lsc-cream tabular-nums">
                  {log.hours.toFixed(1)}
                </td>
                <td className="py-3 px-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-400">
                    {HOUR_LOG_STATUS_LABELS[log.status] ?? log.status}
                  </span>
                </td>
                <td className="py-3 px-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => setVerifyTarget(log)}
                      aria-label={`Verify hours for ${log.volunteer_name || `Volunteer #${log.volunteer_id}`}`}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-status-success-600 text-white hover:bg-status-success-700 transition-colors"
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      Verify
                    </button>
                    <button
                      onClick={() => setRejectTarget(log)}
                      aria-label={`Reject hours for ${log.volunteer_name || `Volunteer #${log.volunteer_id}`}`}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-status-danger-600 text-white hover:bg-status-danger-700 transition-colors"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Reject
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <PaginationControls page={page} total={total} limit={limit} onPageChange={setPage} />
      </div>

      <ConfirmDialog
        isOpen={!!verifyTarget}
        title="Verify Volunteer Hours"
        message={
          verifyTarget ? (
            <div className="space-y-2">
              <p>
                Verify <strong>{verifyTarget.hours.toFixed(1)} hours</strong> logged by{' '}
                <strong>{verifyTarget.volunteer_name || `Volunteer #${verifyTarget.volunteer_id}`}</strong> on{' '}
                {formatDate(verifyTarget.log_date)}?
              </p>
              <p className="text-xs">This adds the hours to their verified total.</p>
            </div>
          ) : ''
        }
        confirmText="Verify"
        confirmVariant="success"
        onConfirm={() => { if (verifyTarget) verifyMut.mutate(verifyTarget.id) }}
        onCancel={() => setVerifyTarget(null)}
        loading={verifyMut.isPending}
      />

      <ConfirmDialog
        isOpen={!!rejectTarget}
        title="Reject Hour Log"
        message={
          rejectTarget ? (
            <div className="space-y-3">
              <p>
                Reject <strong>{rejectTarget.hours.toFixed(1)} hours</strong> logged by{' '}
                <strong>{rejectTarget.volunteer_name || `Volunteer #${rejectTarget.volunteer_id}`}</strong>?
              </p>
              <div>
                <label htmlFor="hour-log-reject-reason" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Reason for rejection
                </label>
                <textarea
                  id="hour-log-reject-reason"
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  rows={3}
                  disabled={rejectMut.isPending}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent disabled:opacity-50"
                  placeholder="Provide a reason for the rejection..."
                />
              </div>
            </div>
          ) : ''
        }
        confirmText="Reject Hours"
        confirmVariant="danger"
        confirmDisabled={rejectReason.trim() === ''}
        onConfirm={() =>
          { if (rejectTarget) rejectMut.mutate({ id: rejectTarget.id, reason: rejectReason.trim() }) }
        }
        onCancel={() => {
          setRejectTarget(null)
          setRejectReason('')
        }}
        loading={rejectMut.isPending}
      />
    </>
  )
}

type Tab = 'applications' | 'roster' | 'shifts' | 'hour_logs'

export default function StaffVolunteerManagementPage(): React.ReactElement {
  const [activeTab, setActiveTab] = useState<Tab>('applications')

  const { data: overview } = useQuery<ProgramOverview>({
    queryKey: ['volunteer-overview'],
    queryFn: () => volunteerApi.getVolunteerProgramOverview(),
  })

  const tabs: { key: Tab; label: string; icon: React.ElementType }[] = [
    { key: 'applications', label: 'Applications', icon: ClipboardList },
    { key: 'roster', label: 'Active Volunteers', icon: UserCheck },
    { key: 'shifts', label: 'Shifts', icon: Calendar },
    { key: 'hour_logs', label: 'Hour Logs', icon: ClipboardCheck },
  ]

  return (
    <AdminShell title="Volunteer Management" subtitle="Review applications and manage the volunteer roster">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          title="Active Volunteers"
          value={overview?.active_volunteers ?? 0}
          icon={Users}
          color="bg-status-success-600"
        />
        <StatCard
          title="Pending Applications"
          value={overview?.pending_applications ?? 0}
          icon={ClipboardList}
          color="bg-lsc-rose"
        />
        <StatCard
          title="Hours This Month"
          value={overview?.total_hours_this_month?.toFixed(1) ?? '0'}
          icon={Clock}
          color="bg-earth-600"
        />
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as Tab)}>
          <TabsList className="px-2">
            {tabs.map(({ key, label, icon: TabIcon }) => (
              <TabsTrigger key={key} value={key} className="flex items-center gap-2">
                <TabIcon className="w-4 h-4" />
                {label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="applications">
            <ApplicationsTab />
          </TabsContent>
          <TabsContent value="roster">
            <RosterTab />
          </TabsContent>
          <TabsContent value="shifts">
            <ShiftsTab />
          </TabsContent>
          <TabsContent value="hour_logs">
            <HourLogsTab />
          </TabsContent>
        </Tabs>
      </div>
    </AdminShell>
  )
}
