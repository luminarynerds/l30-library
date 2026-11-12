/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { AdminShell } from '../components/shells/AdminShell'
import {
  Monitor, Clock, Users, Ticket, BarChart3, Loader2,
  XCircle, CheckCircle, RefreshCw,
  Wifi, Printer as PrinterIcon, Timer,
  Search, X as XIcon, Copy,
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api-client'
import { API_BASE } from '../api/types'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { useFloorViewSocket } from '../hooks/useFloorViewSocket'
import { SocketIndicator, UndoEndSessionToast } from './staff-computers/StaffComputerIndicators'
import { GuestPassesTab } from './staff-computers/GuestPassesTab'
import { StatsTab } from './staff-computers/StatsTab'
import { MaintenanceDialog, RescheduleDialog } from './staff-computers/StaffComputerDialogs'
import {
  BULK_ACTION_LABELS,
  RESERVATION_STATUS_COLORS,
  STATUS_COLORS,
  STATUS_FILTERS,
  TIER_BORDER,
  TYPE_FILTERS,
  TYPE_LABELS,
  UNDO_WINDOW_MS,
  formatMinutes,
  formatTime,
  sortByAttention,
  urgencyTier,
  type BulkAction,
  type FloorComputer,
  type FloorSummary,
  type MaintenanceTarget,
  type StaffReservation,
  type StatusFilter,
  type SystemStats,
  type Tab,
  type TypeFilter,
} from './staff-computers/model'
import { t } from '@/i18n'
import type { GuestPassFormData } from '../features/computers/GuestPassForm'
import { useGuestPasses } from '../features/computers/useGuestPasses'
import {
  EndSessionModal,
  EndReasonRadioGroup,
  type EndReasonCategory,
  type EndSessionTarget,
} from '../components/EndSessionModal'

export default function StaffComputersPage() {
  const [tab, setTab] = useState<Tab>('floor')
  const [loading, setLoading] = useState(true)

  // Floor view state
  const [floor, setFloor] = useState<FloorComputer[]>([])
  const [summary, setSummary] = useState<FloorSummary | null>(null)

  // Reservations state
  const [reservations, setReservations] = useState<StaffReservation[]>([])
  const [resStatusFilter, setResStatusFilter] = useState<string>('')

  // Guest passes state (via hook)
  const { passes, loading: passesLoading, list: listGuestPasses, create: createGuestPass } = useGuestPasses()
  const [createLoading, setCreateLoading] = useState(false)

  // Stats state
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [statsDays, setStatsDays] = useState(7)

  // End-session modal state
  const [endTarget, setEndTarget] = useState<EndSessionTarget | null>(null)
  const [endReason, setEndReason] = useState<EndReasonCategory>('time_up')
  const [endNotes, setEndNotes] = useState('')
  const [endingSession, setEndingSession] = useState(false)

  // Maintenance confirm state
  const [maintTarget, setMaintTarget] = useState<MaintenanceTarget | null>(null)
  const [markingMaint, setMarkingMaint] = useState(false)

  // Floor View filtering + multi-select
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  // Bulk action modal state
  const [bulkAction, setBulkAction] = useState<BulkAction | null>(null)
  const [bulkReason, setBulkReason] = useState<EndReasonCategory>('time_up')
  const [bulkNotes, setBulkNotes] = useState('')
  const [bulkInFlight, setBulkInFlight] = useState(false)

  // Reschedule modal state
  const [rescheduleTarget, setRescheduleTarget] = useState<{ reservationId: number; status: string } | null>(null)
  const [rescheduleStart, setRescheduleStart] = useState('')
  const [rescheduleEnd, setRescheduleEnd] = useState('')
  const [rescheduling, setRescheduling] = useState(false)

  const fetchFloor = useCallback(async () => {
    try {
      const data = await api.get(`${API_BASE}/computers/staff/floor-view`)
      setFloor(data.computers || [])
      setSummary(data.summary || null)
    } catch { toast.error('Failed to load floor view') }
  }, [])

  const fetchReservations = useCallback(async () => {
    try {
      const qs = resStatusFilter ? `?status=${resStatusFilter}` : ""; const data = await api.get(`${API_BASE}/computers/staff/reservations${qs}`)
      setReservations(data.items || [])
    } catch { toast.error('Failed to load reservations') }
  }, [resStatusFilter])

  const fetchStats = useCallback(async () => {
    try {
      const data = await api.get(`${API_BASE}/computers/stats/system?days=${statsDays}`)
      setStats(data)
    } catch { toast.error('Failed to load stats') }
  }, [statsDays])

  useEffect(() => {
    setLoading(true)
    const load = async () => {
      if (tab === 'floor') await fetchFloor()
      else if (tab === 'reservations') await fetchReservations()
      else if (tab === 'guests') await listGuestPasses()
      else if (tab === 'stats') await fetchStats()
      setLoading(false)
    }
    load()
  }, [tab, fetchFloor, fetchReservations, listGuestPasses, fetchStats])

  // Live updates via WebSocket; fall back to polling when not connected.
  const { status: socketStatus } = useFloorViewSocket((event) => {
    if (event.type === 'connected') return
    fetchFloor()
  })

  useEffect(() => {
    if (tab !== 'floor') return
    // Poll fast while we don't have a live socket, slow while we do.
    const intervalMs = socketStatus === 'live' ? 60000 : 30000
    const interval = setInterval(fetchFloor, intervalMs)
    return () => clearInterval(interval)
  }, [tab, fetchFloor, socketStatus])

  const openEndSessionModal = (target: EndSessionTarget) => {
    setEndTarget(target)
    setEndReason('time_up')
    setEndNotes('')
  }

  const closeEndSessionModal = () => {
    if (endingSession) return
    setEndTarget(null)
  }

  const matchesSearch = (comp: FloorComputer, q: string): boolean => {
    if (!q) return true
    const haystack = [
      comp.name,
      comp.computer_number,
      comp.location ?? '',
      comp.active_session?.patron_name ?? '',
    ].join(' ').toLowerCase()
    return haystack.includes(q.toLowerCase())
  }

  const matchesStatus = (comp: FloorComputer, filter: StatusFilter): boolean => {
    if (filter === 'all') return true
    if (filter === 'attention') return urgencyTier(comp) !== 'normal'
    return comp.status === filter
  }

  const matchesType = (comp: FloorComputer, filter: TypeFilter): boolean => {
    if (filter === 'all') return true
    return comp.computer_type === filter
  }

  const filteredFloor = floor.filter(c =>
    matchesSearch(c, searchText) && matchesStatus(c, statusFilter) && matchesType(c, typeFilter)
  )

  const toggleSelected = (computerId: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(computerId)) next.delete(computerId)
      else next.add(computerId)
      return next
    })
  }

  const selectAllVisible = () => {
    setSelectedIds(new Set(filteredFloor.map(c => c.id)))
  }

  const clearSelection = () => setSelectedIds(new Set())

  const openBulkAction = (action: BulkAction) => {
    if (selectedIds.size === 0) return
    setBulkAction(action)
    setBulkReason('time_up')
    setBulkNotes('')
  }

  const closeBulkAction = () => {
    if (bulkInFlight) return
    setBulkAction(null)
  }

  const confirmBulkAction = async () => {
    if (!bulkAction) return
    setBulkInFlight(true)
    const ids = Array.from(selectedIds)
    const payload: Record<string, unknown> = {
      computer_ids: ids,
      action: bulkAction,
    }
    if (bulkAction === 'end_sessions') {
      payload.reason_category = bulkReason
      payload.notes = bulkNotes.trim() || null
    }
    try {
      const result = await api.post(`${API_BASE}/computers/staff/bulk`, payload)
      const succeeded = result?.succeeded ?? 0
      const failed = result?.failed ?? 0
      if (failed === 0) {
        toast.success(`${succeeded} ${succeeded === 1 ? 'computer' : 'computers'} updated`)
      } else {
        toast(
          `${succeeded} succeeded, ${failed} skipped`,
          { icon: '⚠️' },
        )
      }
      setBulkAction(null)
      clearSelection()
      fetchFloor()
    } catch {
      toast.error('Bulk action failed')
    } finally {
      setBulkInFlight(false)
    }
  }

  const handleReopenSession = async (sessionId: number, toastId: string) => {
    toast.dismiss(toastId)
    try {
      await api.post(`${API_BASE}/computers/staff/sessions/${sessionId}/reopen`, {})
      toast.success('Session restored')
      fetchFloor()
    } catch {
      toast.error('Could not restore session — undo window may have expired')
    }
  }

  const confirmEndSession = async () => {
    if (!endTarget) return
    setEndingSession(true)
    const target = endTarget
    try {
      const result = await api.post(
        `${API_BASE}/computers/staff/reservations/${target.reservationId}/end-session`,
        { reason_category: endReason, notes: endNotes.trim() || null },
      )
      setEndTarget(null)
      fetchFloor()
      const sessionId = result?.session_id
      if (typeof sessionId === 'number') {
        toast.custom(
          (t) => (
            <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg px-4 py-3">
              <UndoEndSessionToast
                toastId={t.id}
                sessionId={sessionId}
                patronName={target.patronName}
                onUndo={handleReopenSession}
              />
            </div>
          ),
          { duration: UNDO_WINDOW_MS },
        )
      } else {
        toast.success('Session ended')
      }
    } catch {
      toast.error('Failed to end session')
    } finally {
      setEndingSession(false)
    }
  }

  const openMaintenanceConfirm = (computerId: number, computerName: string) => {
    setMaintTarget({ computerId, computerName })
  }

  const closeMaintenanceConfirm = () => {
    if (markingMaint) return
    setMaintTarget(null)
  }

  const confirmMaintenance = async () => {
    if (!maintTarget) return
    setMarkingMaint(true)
    try {
      await api.patch(`${API_BASE}/admin/computers/${maintTarget.computerId}/status`, { status: 'maintenance' })
      toast.success(`${maintTarget.computerName} marked maintenance`)
      setMaintTarget(null)
      fetchFloor()
    } catch {
      toast.error('Failed to update status')
    } finally {
      setMarkingMaint(false)
    }
  }

  const handleApproveExtension = async (extensionId: number) => {
    try {
      await api.post(`${API_BASE}/computers/extensions/${extensionId}/approve`)
      toast.success('Extension approved')
      fetchFloor()
    } catch { toast.error('Failed to approve extension') }
  }

  const handleToggleStatus = async (computerId: number, newStatus: string) => {
    try {
      await api.patch(`${API_BASE}/admin/computers/${computerId}/status`, { status: newStatus })
      toast.success(`Status updated`)
      fetchFloor()
    } catch { toast.error('Failed to update status') }
  }

  const handleCancelReservation = async (reservationId: number) => {
    try {
      await api.post(`${API_BASE}/computers/reservations/${reservationId}/cancel`)
      toast.success('Reservation cancelled')
      fetchReservations()
    } catch { toast.error('Failed to cancel reservation') }
  }

  // Staff-granted extension on a reservation's active session (no patron request).
  const handleExtend = async (reservationId: number, extraMinutes: number) => {
    try {
      await api.post(`${API_BASE}/computers/staff/reservations/${reservationId}/extend`, { extra_minutes: extraMinutes })
      toast.success(`Extended +${extraMinutes}m`)
      fetchFloor()
    } catch (e) { toast.error(e instanceof Error ? e.message : 'Failed to extend session') }
  }

  // ISO (UTC) -> value for a <input type="datetime-local"> (local wall-clock).
  const toLocalInput = (iso: string): string => {
    const d = new Date(iso)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  }

  const openReschedule = (res: StaffReservation) => {
    setRescheduleTarget({ reservationId: res.id, status: res.status })
    setRescheduleStart(toLocalInput(res.reserved_start_time))
    setRescheduleEnd(toLocalInput(res.reserved_end_time))
  }
  const closeReschedule = () => { if (!rescheduling) setRescheduleTarget(null) }

  const handleRescheduleSubmit = async () => {
    if (!rescheduleTarget) return
    setRescheduling(true)
    try {
      const body: { reserved_start_time?: string; reserved_end_time?: string } = {}
      // A started session's start can't move; backend only honours the end then.
      if (rescheduleTarget.status !== 'in_session') {
        body.reserved_start_time = new Date(rescheduleStart).toISOString()
      }
      body.reserved_end_time = new Date(rescheduleEnd).toISOString()
      await api.patch(`${API_BASE}/computers/staff/reservations/${rescheduleTarget.reservationId}`, body)
      toast.success('Reservation rescheduled')
      setRescheduleTarget(null)
      fetchReservations()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to reschedule')
    } finally {
      setRescheduling(false)
    }
  }

  const handleCreateGuestPassSubmit = async (data: GuestPassFormData) => {
    setCreateLoading(true)
    try {
      const newPass = await createGuestPass(data)
      toast.custom(
        (toastInstance) => (
          <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg px-4 py-3 flex items-center gap-3">
            <div className="text-sm">
              <div className="font-medium text-lsc-dark dark:text-lsc-cream">
                {t('computers.guestPass.passCodeCopied')}
              </div>
              <div className="font-mono text-base text-lsc-dark dark:text-lsc-cream">{newPass.pass_code}</div>
            </div>
            <button
              onClick={() => {
                navigator.clipboard.writeText(newPass.pass_code)
                toast.dismiss(toastInstance.id)
              }}
              className="flex items-center gap-1 px-3 py-1 text-xs rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 whitespace-nowrap"
            >
              <Copy className="w-3 h-3" /> Copy
            </button>
          </div>
        ),
        { duration: 8000 },
      )
      navigator.clipboard.writeText(newPass.pass_code).catch(() => { /* clipboard unavailable */ })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create guest pass')
    } finally {
      setCreateLoading(false)
    }
  }

  const tabs: { key: Tab; label: string; icon: typeof Monitor }[] = [
    { key: 'floor', label: 'Floor View', icon: Monitor },
    { key: 'reservations', label: 'Reservations', icon: Clock },
    { key: 'guests', label: 'Guest Passes', icon: Ticket },
    { key: 'stats', label: 'Stats', icon: BarChart3 },
  ]

  const inputCls = "w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
  const labelCls = "block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"

  return (
    <AdminShell title="Public Computers">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <Monitor className="w-6 h-6 text-lsc-rose" />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Public Computers</h1>
              {summary && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                  {summary.in_use} in use / {summary.available} available / {summary.total} total
                </p>
              )}
            </div>
          </div>
          {tab === 'floor' && (
            <div className="flex items-center gap-3">
              <SocketIndicator status={socketStatus} />
              <button onClick={fetchFloor} className="flex items-center gap-2 px-3 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose">
                <RefreshCw className="w-4 h-4" /> Refresh
              </button>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex border-b border-lsc-border dark:border-earth-700 mb-6">
          {tabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === key
                  ? 'border-lsc-rose text-lsc-rose'
                  : 'border-transparent text-earth-600 dark:text-earth-400 hover:text-earth-700 dark:hover:text-earth-200'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
              {key === 'floor' && summary && summary.pending_extensions > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400 rounded-full">
                  {summary.pending_extensions}
                </span>
              )}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : (
          <>
            {/* Floor View */}
            {tab === 'floor' && (
              <>
                {(() => {
                  const attentionCount = floor.filter(c => urgencyTier(c) !== 'normal').length
                  if (attentionCount === 0) return null
                  return (
                    <div className="mb-4 flex items-center gap-3 px-4 py-3 rounded-xl bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-700">
                      <Timer className="w-5 h-5 text-status-warning-700 dark:text-status-warning-400" />
                      <div className="text-sm text-status-warning-800 dark:text-status-warning-300">
                        <span className="font-medium">{attentionCount}</span> {attentionCount === 1 ? 'computer needs' : 'computers need'} attention
                      </div>
                    </div>
                  )
                })()}

                {/* Filter toolbar */}
                <div className="mb-4 space-y-3">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/40 dark:text-lsc-cream/40" />
                    <input
                      type="text"
                      value={searchText}
                      onChange={e => setSearchText(e.target.value)}
                      placeholder="Search by name, number, location, or patron…"
                      className="w-full pl-9 pr-9 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    />
                    {searchText && (
                      <button
                        onClick={() => setSearchText('')}
                        aria-label={t('aria.staffComputers.clearSearch', 'Clear search')}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-lsc-dark/40 dark:text-lsc-cream/40 hover:text-lsc-rose"
                      >
                        <XIcon className="w-4 h-4" />
                      </button>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {STATUS_FILTERS.map(f => (
                      <button
                        key={f.value}
                        onClick={() => setStatusFilter(f.value)}
                        className={`px-3 py-1 rounded-full text-xs font-medium border ${
                          statusFilter === f.value
                            ? 'bg-lsc-rose text-white border-lsc-rose'
                            : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-600 hover:bg-lsc-cream dark:hover:bg-earth-700'
                        }`}
                      >
                        {f.label}
                      </button>
                    ))}
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {TYPE_FILTERS.map(f => (
                      <button
                        key={f.value}
                        onClick={() => setTypeFilter(f.value)}
                        className={`px-3 py-1 rounded-full text-xs font-medium border ${
                          typeFilter === f.value
                            ? 'bg-lsc-dark text-lsc-cream border-lsc-dark dark:bg-lsc-cream dark:text-lsc-dark dark:border-lsc-cream'
                            : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-600 hover:bg-lsc-cream dark:hover:bg-earth-700'
                        }`}
                      >
                        {f.label}
                      </button>
                    ))}
                  </div>

                  {filteredFloor.length > 0 && (
                    <div className="flex items-center gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                      <span>{filteredFloor.length} of {floor.length} shown</span>
                      <button onClick={selectAllVisible} className="text-lsc-rose hover:underline">
                        Select all visible
                      </button>
                      {selectedIds.size > 0 && (
                        <button onClick={clearSelection} className="text-lsc-rose hover:underline">
                          Clear ({selectedIds.size})
                        </button>
                      )}
                    </div>
                  )}
                </div>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...filteredFloor].sort(sortByAttention).map(comp => (
                  <div key={comp.id} className={`bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border ${TIER_BORDER[urgencyTier(comp)]} ${selectedIds.has(comp.id) ? 'ring-2 ring-lsc-rose' : ''}`}>
                    {/* Computer header */}
                    <div className="flex justify-between items-start mb-2 gap-2">
                      <div className="flex items-start gap-2 min-w-0">
                        <button
                          onClick={() => toggleSelected(comp.id)}
                          aria-label={selectedIds.has(comp.id) ? 'Deselect' : 'Select'}
                          className={`mt-1 shrink-0 w-5 h-5 rounded border flex items-center justify-center ${
                            selectedIds.has(comp.id)
                              ? 'bg-lsc-rose border-lsc-rose text-white'
                              : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-600 hover:border-lsc-rose'
                          }`}
                        >
                          {selectedIds.has(comp.id) && <CheckCircle className="w-4 h-4" />}
                        </button>
                        <div className="min-w-0">
                          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate">{comp.name}</h3>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate">{comp.location}</p>
                        </div>
                      </div>
                      <span className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[comp.status] || 'bg-earth-100 dark:bg-earth-700'}`}>
                        {comp.status.replace('_', ' ')}
                      </span>
                    </div>

                    {/* Tags */}
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs text-lsc-dark dark:text-lsc-cream">
                        {TYPE_LABELS[comp.computer_type] || comp.computer_type}
                      </span>
                      {comp.has_internet && (
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs">
                          <Wifi className="w-3 h-3" />Net
                        </span>
                      )}
                      {comp.has_print_release && (
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs">
                          <PrinterIcon className="w-3 h-3" />Print
                        </span>
                      )}
                    </div>

                    {/* Active session info */}
                    {comp.active_session ? (
                      <div className="bg-status-info-50 dark:bg-status-info-900/20 rounded-lg p-3 mb-3 space-y-1.5">
                        <div className="flex items-center gap-2">
                          <Users className="w-4 h-4 text-status-info-600 dark:text-status-info-400" />
                          <span className="text-sm font-medium text-status-info-800 dark:text-status-info-300">
                            {comp.active_session.patron_name || 'Unknown patron'}
                          </span>
                          {comp.active_session.is_guest && (
                            <span className="text-xs px-1.5 py-0.5 bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-400 rounded">Guest</span>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                          <span className="flex items-center gap-1">
                            <Timer className="w-3 h-3" />
                            {comp.active_session.is_overtime ? (
                              <span className="text-status-danger-600 dark:text-status-danger-400 font-bold">
                                {comp.active_session.minutes_overtime ?? 0}m over
                              </span>
                            ) : (
                              <span className={comp.active_session.minutes_remaining <= 5 ? 'text-status-danger-600 dark:text-status-danger-400 font-bold' : ''}>
                                {comp.active_session.minutes_remaining}m left
                              </span>
                            )}
                          </span>
                          <span>Started {formatTime(comp.active_session.started_at)}</span>
                          {comp.active_session.extensions_used > 0 && (
                            <span>+{comp.active_session.extensions_used} ext</span>
                          )}
                          {comp.active_session.print_jobs_count > 0 && (
                            <span className="flex items-center gap-1"><PrinterIcon className="w-3 h-3" />{comp.active_session.print_jobs_count}</span>
                          )}
                        </div>
                      </div>
                    ) : comp.status === 'available' ? (
                      <div className="text-sm text-status-success-600 dark:text-status-success-400 mb-3">Ready for use</div>
                    ) : null}

                    {/* Pending extension request */}
                    {comp.pending_extension && (
                      <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-700 rounded-lg p-2 mb-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-status-warning-800 dark:text-status-warning-300">
                            Extension request: +{comp.pending_extension.extension_minutes}m
                          </span>
                          <button
                            onClick={() => handleApproveExtension(comp.pending_extension!.id)}
                            className="text-xs px-2 py-1 bg-status-success-100 text-status-success-800 hover:bg-status-success-200 dark:bg-status-success-900/30 dark:text-status-success-400 rounded"
                          >
                            <CheckCircle className="w-3 h-3 inline mr-1" />Approve
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-1.5 flex-wrap">
                      {comp.active_session && (
                        <>
                          <button
                            onClick={() => openEndSessionModal({
                              reservationId: comp.active_session!.reservation_id,
                              patronName: comp.active_session!.patron_name,
                              minutesRemaining: comp.active_session!.minutes_remaining,
                            })}
                            className="text-xs px-2 py-1 rounded bg-status-danger-100 text-status-danger-800 hover:bg-status-danger-200 dark:bg-status-danger-900/30 dark:text-status-danger-400"
                          >
                            <XCircle className="w-3 h-3 inline mr-1" />End Session
                          </button>
                          <button
                            onClick={() => handleExtend(comp.active_session!.reservation_id, 15)}
                            className="text-xs px-2 py-1 rounded bg-status-success-100 text-status-success-800 hover:bg-status-success-200 dark:bg-status-success-900/30 dark:text-status-success-400"
                          >
                            +15m
                          </button>
                          <button
                            onClick={() => handleExtend(comp.active_session!.reservation_id, 30)}
                            className="text-xs px-2 py-1 rounded bg-status-success-100 text-status-success-800 hover:bg-status-success-200 dark:bg-status-success-900/30 dark:text-status-success-400"
                          >
                            +30m
                          </button>
                        </>
                      )}
                      {comp.status !== 'available' && !comp.active_session && (
                        <button onClick={() => handleToggleStatus(comp.id, 'available')}
                          className="text-xs px-2 py-1 rounded bg-status-success-100 text-status-success-800 hover:bg-status-success-200 dark:bg-status-success-900/30 dark:text-status-success-400">
                          Available
                        </button>
                      )}
                      {comp.status !== 'maintenance' && !comp.active_session && (
                        <button onClick={() => openMaintenanceConfirm(comp.id, comp.name)}
                          className="text-xs px-2 py-1 rounded bg-status-warning-100 text-status-warning-800 hover:bg-status-warning-200 dark:bg-status-warning-900/30 dark:text-status-warning-400">
                          Maintenance
                        </button>
                      )}
                    </div>
                  </div>
                ))}
                {floor.length === 0 && (
                  <div className="col-span-full text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/60">
                    <Monitor className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No computers configured</p>
                  </div>
                )}
                {floor.length > 0 && filteredFloor.length === 0 && (
                  <div className="col-span-full text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/60">
                    <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No computers match the current filters</p>
                  </div>
                )}
              </div>
              </>
            )}

            {/* Reservations */}
            {tab === 'reservations' && (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <select
                    value={resStatusFilter}
                    onChange={e => setResStatusFilter(e.target.value)}
                    aria-label={t('aria.staffComputers.filterReservationsByStatus', 'Filter reservations by status')}
                    className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
                  >
                    <option value="">All statuses</option>
                    <option value="pending">Pending</option>
                    <option value="confirmed">Confirmed</option>
                    <option value="in_session">In Session</option>
                    <option value="completed">Completed</option>
                    <option value="cancelled">Cancelled</option>
                    <option value="no_show">No Show</option>
                  </select>
                  <button onClick={fetchReservations} className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose">
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>

                {reservations.length === 0 ? (
                  <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/60">
                    <Clock className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>No reservations today</p>
                  </div>
                ) : (
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-lsc-cream/50 dark:bg-earth-700/50 text-left text-lsc-dark/70 dark:text-lsc-cream/70">
                          <th className="px-4 py-3 font-medium">Time</th>
                          <th className="px-4 py-3 font-medium">Patron</th>
                          <th className="px-4 py-3 font-medium">Computer</th>
                          <th className="px-4 py-3 font-medium">Duration</th>
                          <th className="px-4 py-3 font-medium">Status</th>
                          <th className="px-4 py-3 font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                        {reservations.map(res => (
                          <tr key={res.id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                            <td className="px-4 py-3 whitespace-nowrap">
                              <div>{formatTime(res.reserved_start_time)}</div>
                              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">to {formatTime(res.reserved_end_time)}</div>
                            </td>
                            <td className="px-4 py-3">
                              <div className="text-lsc-dark dark:text-lsc-cream">{res.patron_name || 'Unknown'}</div>
                              {res.is_guest_pass && (
                                <span className="text-xs px-1.5 py-0.5 bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-400 rounded">Guest</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{res.computer_name}</td>
                            <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{formatMinutes(res.session_duration_minutes)}</td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${RESERVATION_STATUS_COLORS[res.status] || 'bg-earth-100 dark:bg-earth-700'}`}>
                                {res.status.replace('_', ' ')}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex gap-1.5">
                                {['pending', 'confirmed', 'in_session'].includes(res.status) && (
                                  <button
                                    onClick={() => openReschedule(res)}
                                    className="text-xs px-2 py-1 rounded bg-earth-100 text-lsc-dark/80 hover:bg-earth-200 dark:bg-earth-700 dark:text-lsc-cream/80 dark:hover:bg-earth-600"
                                  >
                                    Edit time
                                  </button>
                                )}
                                {['pending', 'confirmed'].includes(res.status) && (
                                  <button
                                    onClick={() => handleCancelReservation(res.id)}
                                    className="text-xs px-2 py-1 rounded bg-status-danger-100 text-status-danger-800 hover:bg-status-danger-200 dark:bg-status-danger-900/30 dark:text-status-danger-400"
                                  >
                                    Cancel
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {tab === 'guests' && (
              <GuestPassesTab
                passes={passes}
                loading={passesLoading}
                creating={createLoading}
                onCreate={handleCreateGuestPassSubmit}
              />
            )}

            {tab === 'stats' && (
              <StatsTab stats={stats} days={statsDays} onDaysChange={setStatsDays} />
            )}
          </>
        )}

        {/* Bulk Action Bar — sticky bottom when items selected on Floor View */}
        {tab === 'floor' && selectedIds.size > 0 && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-30 bg-lsc-dark dark:bg-earth-800 text-lsc-cream rounded-xl shadow-lg px-4 py-3 flex items-center gap-3">
            <span className="text-sm font-medium">
              {selectedIds.size} selected
            </span>
            <span className="w-px h-5 bg-lsc-cream/30" />
            <button
              onClick={() => openBulkAction('end_sessions')}
              className="text-xs px-3 py-1.5 rounded-lg bg-status-danger-600 hover:bg-status-danger-700"
            >
              End Sessions
            </button>
            <button
              onClick={() => openBulkAction('mark_available')}
              className="text-xs px-3 py-1.5 rounded-lg bg-status-success-600 hover:bg-status-success-700"
            >
              Available
            </button>
            <button
              onClick={() => openBulkAction('mark_maintenance')}
              className="text-xs px-3 py-1.5 rounded-lg bg-status-warning-600 hover:bg-status-warning-700"
            >
              Maintenance
            </button>
            <button
              onClick={() => openBulkAction('mark_offline')}
              className="text-xs px-3 py-1.5 rounded-lg bg-earth-600 hover:bg-earth-700"
            >
              Offline
            </button>
            <button
              onClick={clearSelection}
              aria-label="Clear selection"
              className="ml-1 text-lsc-cream/70 hover:text-lsc-cream"
            >
              <XIcon className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Bulk Action Modal */}
        {bulkAction && (
          <ModalBackdrop onClose={closeBulkAction} title={BULK_ACTION_LABELS[bulkAction]}>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                  {BULK_ACTION_LABELS[bulkAction]}
                </h3>
                <button onClick={closeBulkAction} disabled={bulkInFlight} aria-label={t('aria.addRoleModal.closeModal')}>
                  <XCircle className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" />
                </button>
              </div>
              <div className="p-4 space-y-4">
                <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                  Apply <span className="font-medium">{BULK_ACTION_LABELS[bulkAction]}</span> to <span className="font-medium">{selectedIds.size}</span> {selectedIds.size === 1 ? 'computer' : 'computers'}?
                </p>
                {bulkAction === 'end_sessions' && (
                  <>
                    <div>
                      <label className={labelCls}>Reason</label>
                      <EndReasonRadioGroup
                        name="bulk-end-reason"
                        value={bulkReason}
                        onChange={setBulkReason}
                      />
                    </div>
                    <div>
                      <label className={labelCls}>
                        Notes {bulkReason === 'other' && <span className="text-status-danger-600">*</span>}
                      </label>
                      <textarea
                        value={bulkNotes}
                        onChange={e => setBulkNotes(e.target.value)}
                        rows={2}
                        maxLength={500}
                        placeholder="Optional context applied to all ended sessions"
                        className={inputCls + ' resize-none'}
                      />
                    </div>
                  </>
                )}
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                  Computers that aren't eligible (e.g. no active session) will be skipped; the rest will succeed.
                </p>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={closeBulkAction}
                    disabled={bulkInFlight}
                    className="px-4 py-2 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={confirmBulkAction}
                    disabled={bulkInFlight || (bulkAction === 'end_sessions' && bulkReason === 'other' && !bulkNotes.trim())}
                    className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2"
                  >
                    {bulkInFlight && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                    Confirm
                  </button>
                </div>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {maintTarget && (
          <MaintenanceDialog
            target={maintTarget}
            pending={markingMaint}
            onClose={closeMaintenanceConfirm}
            onConfirm={confirmMaintenance}
          />
        )}

        {/* End Session Confirmation Modal */}
        {endTarget && (
          <EndSessionModal
            endTarget={endTarget}
            endReason={endReason}
            endNotes={endNotes}
            endingSession={endingSession}
            onClose={closeEndSessionModal}
            onChangeReason={setEndReason}
            onChangeNotes={setEndNotes}
            onConfirm={confirmEndSession}
          />
        )}

        {rescheduleTarget && (
          <RescheduleDialog
            status={rescheduleTarget.status}
            start={rescheduleStart}
            end={rescheduleEnd}
            pending={rescheduling}
            onStartChange={setRescheduleStart}
            onEndChange={setRescheduleEnd}
            onClose={closeReschedule}
            onConfirm={handleRescheduleSubmit}
          />
        )}

      </div>
    </AdminShell>
  )
}
