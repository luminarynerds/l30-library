/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Calendar,
  MapPin,
  Users,
  Printer,
  CheckCircle2,
  UserPlus,
  Accessibility,
  Loader2,
  ClipboardCheck,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'
import { useTranslation } from '@/i18n/I18nContext'
import { AdminShell } from '../components/shells/AdminShell'
import { getCurrentLocale } from '@/i18n'
import {
  getEvent,
  getEventRegistrations,
  acknowledgeAccommodation,
  adminCancelRegistration,
  markRegistrationNoShow,
  markRegistrationAttended,
  type Registration,
  type Event as EventModel,
} from '@/api/events-api'
import {
  listAttendanceSessions,
  createAttendanceSession,
  checkInWalkIn,
  type AttendanceSession,
} from '@/api/domains/services/attendance-api'

const STAFF_ROLES = ['admin', 'super_admin', 'director', 'staff']

function formatDateTime(s: string): string {
  return new Date(s).toLocaleDateString(getCurrentLocale(), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'confirmed':
      return 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-200'
    case 'waitlisted':
      return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-200'
    case 'cancelled':
      return 'bg-lsc-cream text-lsc-dark/70 dark:bg-earth-700 dark:text-lsc-cream/70'
    case 'no_show':
      return 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-200'
    default:
      return 'bg-lsc-cream text-lsc-dark/70 dark:bg-earth-700 dark:text-lsc-cream/70'
  }
}

async function ensureAttendanceSession(event: EventModel): Promise<AttendanceSession> {
  const existing = await listAttendanceSessions({ per_page: 50 })
  const match = existing.data.find((s) => s.event_id === event.id)
  if (match) return match
  return await createAttendanceSession({
    event_id: event.id,
    session_name: event.title,
    session_date: event.start_time.slice(0, 10),
  })
}

interface WalkInFormState {
  guest_name: string
  guest_email: string
  age_range: string
}

const AGE_RANGES = ['unknown', '0-5', '6-12', '13-17', '18-34', '35-54', '55-64', '65+']

export default function EventRosterPage(): React.ReactElement {
  const { t } = useTranslation()
  const { eventId: eventIdParam } = useParams<{ eventId: string }>()
  const eventId = Number(eventIdParam)
  const navigate = useNavigate()
  const { user, token } = useAuth()
  const queryClient = useQueryClient()
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [walkIn, setWalkIn] = useState<WalkInFormState>({
    guest_name: '',
    guest_email: '',
    age_range: 'unknown',
  })
  const [ackedThisSession, setAckedThisSession] = useState<Set<number>>(new Set())

  const isStaffUser = !!user && STAFF_ROLES.includes(user.role)

  const eventQuery = useQuery({
    queryKey: ['event', eventId],
    queryFn: () => getEvent(eventId),
    enabled: Number.isFinite(eventId) && isStaffUser,
  })

  const rosterQuery = useQuery({
    queryKey: ['event-roster', eventId],
    queryFn: () =>
      getEventRegistrations(token || '', eventId, { includeWaitlist: true, perPage: 200 }),
    enabled: Number.isFinite(eventId) && !!token && isStaffUser,
    retry: (failureCount, error: unknown) => {
      // 403 → don't retry, route handler below will redirect.
      const status = (error as { status?: number } | undefined)?.status
      if (status === 403) return false
      return failureCount < 2
    },
  })

  // 403 redirect: matches the codebase's pattern of bouncing non-staff to /.
  if (rosterQuery.isError) {
    const status = (rosterQuery.error as { status?: number } | undefined)?.status
    if (status === 403) {
      toast.error(t('events.roster.accessDenied', 'You do not have permission to view this roster.'))
      navigate('/')
    }
  }

  const event = eventQuery.data
  const roster = rosterQuery.data
  const registrations = useMemo(
    () => roster?.registrations ?? [],
    [roster]
  )
  // 'In the past' = the event has ended. We use end_time when present, else
  // start_time + 24h as a generous grace window so day-of reconciliation
  // (the whole reason this page exists) still works after the start_time.
  const eventInPast = useMemo(() => {
    if (!event) return false
    const now = new Date()
    if (event.end_time) return new Date(event.end_time) < now
    const grace = new Date(event.start_time)
    grace.setHours(grace.getHours() + 24)
    return grace < now
  }, [event])

  const confirmedCount = useMemo(
    () => registrations.filter((r) => r.status === 'confirmed').length,
    [registrations]
  )
  const waitlistedCount = useMemo(
    () => registrations.filter((r) => r.status === 'waitlisted').length,
    [registrations]
  )

  const acknowledgeMutation = useMutation({
    mutationFn: (registrationId: number) =>
      acknowledgeAccommodation(token || '', eventId, registrationId),
    onSuccess: (_, registrationId) => {
      setAckedThisSession((prev) => new Set(prev).add(registrationId))
      queryClient.invalidateQueries({ queryKey: ['event-roster', eventId] })
      toast.success(t('events.roster.accommodationAcknowledged', 'Accommodation acknowledged'))
    },
    onError: (err: Error) => {
      toast.error(err.message || t('events.roster.acknowledgeFailed', 'Failed to acknowledge'))
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (registrationId: number) =>
      adminCancelRegistration(token || '', eventId, registrationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['event-roster', eventId] })
      toast.success(t('events.roster.registrationCancelled', 'Registration cancelled'))
    },
    onError: (err: Error) => {
      toast.error(err.message || t('events.roster.cancelFailed', 'Failed to cancel'))
    },
  })

  const markAttendedMutation = useMutation({
    mutationFn: async (regs: Registration[]) => {
      if (!event) throw new Error('Event not loaded')
      // Pre-registered attendance now uses the dedicated registration
      // → check-in endpoint, which creates an AttendanceCheckIn with
      // check_in_method='pre_registered' and registration_id set so
      // attribution rolls up correctly (total_pre_registered, not
      // total_walk_ins). The backend lazily ensures an AttendanceSession
      // exists for the event. Walk-ins below still use the original
      // walk_in path because they have no registration to link to.
      await Promise.all(
        regs.map((reg) =>
          markRegistrationAttended(token || '', eventId, reg.id)
        )
      )
      return regs.length
    },
    onSuccess: (count) => {
      queryClient.invalidateQueries({ queryKey: ['event-roster', eventId] })
      setSelectedIds(new Set())
      toast.success(
        t('events.roster.markedAttended', 'Marked {{count}} attended').replace(
          '{{count}}',
          String(count)
        )
      )
    },
    onError: (err: Error) => {
      toast.error(err.message || t('events.roster.markAttendedFailed', 'Failed to mark attended'))
    },
  })

  const markNoShowMutation = useMutation({
    mutationFn: async (regs: Registration[]) => {
      // Promise.all over the sequenced calls — the backend endpoint is
      // idempotent so a partial failure on retry will not re-mark already-
      // no_show registrations.
      const results = await Promise.all(
        regs.map((reg) => markRegistrationNoShow(token || '', eventId, reg.id))
      )
      return results.length
    },
    onSuccess: (count) => {
      queryClient.invalidateQueries({ queryKey: ['event-roster', eventId] })
      setSelectedIds(new Set())
      toast.success(
        t('events.roster.markedNoShow', 'Marked {{count}} no-show').replace(
          '{{count}}',
          String(count)
        )
      )
    },
    onError: (err: Error) => {
      toast.error(err.message || t('events.roster.markNoShowFailed', 'Failed to mark no-show'))
    },
  })

  const walkInMutation = useMutation({
    mutationFn: async () => {
      if (!event) throw new Error('Event not loaded')
      if (!walkIn.guest_name.trim()) throw new Error('Walk-in name required')
      const session = await ensureAttendanceSession(event)
      const payload: { session_id: number; guest_name: string; guest_email?: string; age_range?: string } = {
        session_id: session.id,
        guest_name: walkIn.guest_name.trim(),
      }
      const emailTrim = walkIn.guest_email.trim()
      if (emailTrim) payload.guest_email = emailTrim
      if (walkIn.age_range) payload.age_range = walkIn.age_range
      return await checkInWalkIn(payload)
    },
    onSuccess: () => {
      setWalkIn({ guest_name: '', guest_email: '', age_range: 'unknown' })
      toast.success(t('events.roster.walkInAdded', 'Walk-in added'))
    },
    onError: (err: Error) => {
      toast.error(err.message || t('events.roster.walkInFailed', 'Failed to add walk-in'))
    },
  })

  function toggleAll(checked: boolean) {
    if (checked) setSelectedIds(new Set(registrations.map((r) => r.id)))
    else setSelectedIds(new Set())
  }
  function toggleOne(id: number, checked: boolean) {
    const next = new Set(selectedIds)
    if (checked) next.add(id)
    else next.delete(id)
    setSelectedIds(next)
  }

  function handleBulkAttended() {
    const regs = registrations.filter((r) => selectedIds.has(r.id))
    if (regs.length === 0) return
    markAttendedMutation.mutate(regs)
  }

  function handleBulkNoShow() {
    const regs = registrations.filter((r) => selectedIds.has(r.id))
    if (regs.length === 0) return
    markNoShowMutation.mutate(regs)
  }

  function handlePrint() {
    window.print()
  }

  if (!isStaffUser) {
    return (
      <AdminShell title={t('events.roster.staffOnly', 'Staff Only')}>
        <div className="max-w-2xl mx-auto text-center py-12">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            {t('events.roster.staffOnlyMessage', 'Staff access required to view event rosters.')}
          </p>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-lsc-rose text-white rounded-xl"
          >
            {t('events.roster.goHome', 'Go home')}
          </button>
        </div>
      </AdminShell>
    )
  }

  if (!Number.isFinite(eventId)) {
    return (
      <AdminShell title={t('events.roster.title', 'Event Roster')}>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('events.roster.invalidEvent', 'Invalid event ID.')}
        </p>
      </AdminShell>
    )
  }

  if (eventQuery.isLoading || rosterQuery.isLoading) {
    return (
      <AdminShell title={t('events.roster.title', 'Event Roster')} loading>
        <span />
      </AdminShell>
    )
  }

  return (
    <AdminShell
      title={event ? event.title : t('events.roster.title', 'Event Roster')}
      icon={<ClipboardCheck size={28} />}
      subtitle={t('events.roster.subtitle', 'Registered patrons + day-of attendance')}
      actions={
        <div className="flex items-center gap-2 no-print">
          <Link
            to="/staff/events"
            className="inline-flex items-center gap-1 px-3 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl"
          >
            <ArrowLeft className="w-4 h-4" />
            {t('events.roster.backToEvents', 'Back to events')}
          </Link>
          <button
            onClick={handlePrint}
            className="inline-flex items-center gap-1 px-3 py-2 text-sm bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl hover:bg-lsc-border"
          >
            <Printer className="w-4 h-4" />
            {t('events.roster.printRoster', 'Print roster')}
          </button>
        </div>
      }
    >
      <PrintStyles />
      <div className="space-y-6 print-area">
        {/* Event header */}
        {event && (
          <section
            aria-label={t('events.roster.eventDetailsAria', 'Event details')}
            className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700"
          >
            <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              {event.title}
            </h2>
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
              <span className="inline-flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {formatDateTime(event.start_time)}
              </span>
              {event.location && (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  {event.location}
                </span>
              )}
              <span className="inline-flex items-center gap-1">
                <Users className="w-4 h-4" />
                {event.max_attendees
                  ? t('events.roster.capacityCounts', '{{confirmed}} / {{max}} confirmed, {{waitlist}} on waitlist')
                      .replace('{{confirmed}}', String(confirmedCount))
                      .replace('{{max}}', String(event.max_attendees))
                      .replace('{{waitlist}}', String(waitlistedCount))
                  : t('events.roster.capacityCountsNoMax', '{{confirmed}} confirmed, {{waitlist}} on waitlist')
                      .replace('{{confirmed}}', String(confirmedCount))
                      .replace('{{waitlist}}', String(waitlistedCount))}
              </span>
            </div>
          </section>
        )}

        {/* Bulk actions. Disabled when nothing selected or the event has
            already ended (read-only mode per spec). */}
        <section className="no-print flex flex-wrap items-center gap-2" aria-label="Bulk actions">
          <button
            type="button"
            disabled={selectedIds.size === 0 || eventInPast || markAttendedMutation.isPending}
            onClick={handleBulkAttended}
            className="inline-flex items-center gap-1 px-3 py-2 text-sm bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-disabled={selectedIds.size === 0 || eventInPast}
          >
            <CheckCircle2 className="w-4 h-4" />
            {t('events.roster.bulkAttended', 'Mark selected attended')} ({selectedIds.size})
          </button>
          <button
            type="button"
            disabled={selectedIds.size === 0 || markNoShowMutation.isPending}
            onClick={handleBulkNoShow}
            className="inline-flex items-center gap-1 px-3 py-2 text-sm bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-disabled={selectedIds.size === 0}
          >
            {t('events.roster.bulkNoShow', 'Mark selected no-show')} ({selectedIds.size})
          </button>
        </section>

        {/* Registrants table */}
        <section
          className="bg-lsc-white dark:bg-earth-800 rounded-xl overflow-hidden border border-lsc-border dark:border-earth-700"
          aria-label={t('events.roster.registrantsTableAria', 'Registered patrons')}
        >
          {registrations.length === 0 ? (
            <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('events.roster.empty', 'No one has signed up yet.')}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-lsc-cream dark:bg-lsc-brown">
                  <tr>
                    <th scope="col" className="px-3 py-3 text-left no-print w-10">
                      <input
                        type="checkbox"
                        aria-label={t('events.roster.selectAll', 'Select all')}
                        checked={selectedIds.size > 0 && selectedIds.size === registrations.length}
                        onChange={(e) => toggleAll(e.target.checked)}
                      />
                    </th>
                    <th scope="col" className="px-3 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('events.roster.colName', 'Name')}
                    </th>
                    <th scope="col" className="px-3 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('events.roster.colEmail', 'Email')}
                    </th>
                    <th scope="col" className="px-3 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('events.roster.colStatus', 'Status')}
                    </th>
                    <th scope="col" className="px-3 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('events.roster.colAccommodation', 'Accommodation')}
                    </th>
                    <th scope="col" className="px-3 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('events.roster.colRegistered', 'Registered')}
                    </th>
                    <th scope="col" className="px-3 py-3 text-right font-semibold text-lsc-dark dark:text-lsc-cream no-print">
                      {t('events.roster.colActions', 'Actions')}
                    </th>
                    <th scope="col" className="px-3 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream print-only">
                      {t('events.roster.colSignature', 'Signature')}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {registrations.map((r) => {
                    // API field is source of truth so the "Acknowledged" pill
                    // survives a hard refresh. ackedThisSession is still
                    // consulted as an optimistic-update layer so the UI flips
                    // before the roster query re-fetch completes.
                    const isAcked =
                      r.accommodation_acknowledged_at != null ||
                      ackedThisSession.has(r.id)
                    const showAck =
                      r.accommodation_requested === true && !isAcked
                    return (
                      <tr key={r.id} className="hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/50">
                        <td className="px-3 py-3 no-print">
                          <input
                            type="checkbox"
                            aria-label={`Select ${r.patron_name}`}
                            checked={selectedIds.has(r.id)}
                            onChange={(e) => toggleOne(r.id, e.target.checked)}
                          />
                        </td>
                        <td className="px-3 py-3 font-medium text-lsc-dark dark:text-lsc-cream">
                          {r.patron_name}
                        </td>
                        <td className="px-3 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">
                          {r.patron_email}
                        </td>
                        <td className="px-3 py-3">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusBadgeClass(r.status)}`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="px-3 py-3">
                          {r.accommodation_requested ? (
                            showAck ? (
                              <button
                                type="button"
                                onClick={() => acknowledgeMutation.mutate(r.id)}
                                disabled={acknowledgeMutation.isPending}
                                className="inline-flex items-center gap-1 px-2 py-1 text-xs border border-lsc-rose text-lsc-rose rounded-xl hover:bg-lsc-rose hover:text-white"
                              >
                                <Accessibility className="w-3 h-3" />
                                {t('events.roster.acknowledge', 'Acknowledge')}
                              </button>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-200">
                                <CheckCircle2 className="w-3 h-3" />
                                {t('events.roster.acknowledged', 'Acknowledged')}
                              </span>
                            )
                          ) : (
                            <span className="text-lsc-dark/50 dark:text-lsc-cream/50">—</span>
                          )}
                          {r.accommodation_details && (
                            <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 max-w-xs">
                              {r.accommodation_details}
                            </p>
                          )}
                        </td>
                        <td className="px-3 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">
                          {formatDateTime(r.registered_at)}
                        </td>
                        <td className="px-3 py-3 text-right no-print">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => markAttendedMutation.mutate([r])}
                              disabled={markAttendedMutation.isPending}
                              className="px-2 py-1 text-xs bg-lsc-rose text-white rounded hover:bg-lsc-rose/90 disabled:opacity-50"
                            >
                              {t('events.roster.markAttended', 'Mark attended')}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                if (window.confirm(t('events.roster.cancelConfirm', 'Cancel this registration?'))) {
                                  cancelMutation.mutate(r.id)
                                }
                              }}
                              disabled={cancelMutation.isPending}
                              className="px-2 py-1 text-xs border border-status-danger-300 text-status-danger-700 dark:text-status-danger-300 rounded hover:bg-status-danger-50 dark:hover:bg-status-danger-900/30"
                            >
                              {t('events.roster.cancel', 'Cancel')}
                            </button>
                          </div>
                        </td>
                        <td className="px-3 py-3 print-only"></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Walk-in form */}
        <section
          className="no-print bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700"
          aria-label={t('events.roster.walkInAria', 'Add walk-in attendee')}
        >
          <h3 className="text-base font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
            <UserPlus className="w-4 h-4" />
            {t('events.roster.walkInHeading', 'Add walk-in')}
          </h3>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              walkInMutation.mutate()
            }}
            className="flex flex-wrap gap-2 items-end"
          >
            <label className="flex flex-col text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('events.roster.walkInName', 'Name')}
              <input
                type="text"
                value={walkIn.guest_name}
                onChange={(e) => setWalkIn({ ...walkIn, guest_name: e.target.value })}
                className="mt-1 px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                required
              />
            </label>
            <label className="flex flex-col text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('events.roster.walkInEmail', 'Email (optional)')}
              <input
                type="email"
                value={walkIn.guest_email}
                onChange={(e) => setWalkIn({ ...walkIn, guest_email: e.target.value })}
                className="mt-1 px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </label>
            <label className="flex flex-col text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('events.roster.walkInAge', 'Age band')}
              <select
                value={walkIn.age_range}
                onChange={(e) => setWalkIn({ ...walkIn, age_range: e.target.value })}
                className="mt-1 px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              >
                {AGE_RANGES.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </label>
            <button
              type="submit"
              disabled={walkInMutation.isPending || !walkIn.guest_name.trim()}
              className="px-4 py-2 text-sm bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1"
            >
              {walkInMutation.isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              {t('events.roster.walkInAdd', 'Add')}
            </button>
          </form>
        </section>
      </div>
    </AdminShell>
  )
}

function PrintStyles(): React.ReactElement {
  return (
    <style>{`
      .print-only { display: none; }
      @media print {
        body { background: white !important; color: black !important; }
        nav, header, footer, aside, .no-print { display: none !important; }
        .print-only { display: table-cell !important; }
        .print-area { box-shadow: none !important; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #999; padding: 6px 8px; }
      }
    `}</style>
  )
}
