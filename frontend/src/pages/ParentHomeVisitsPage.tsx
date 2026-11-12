/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import * as Sentry from "@/lib/sentry-lazy"
import {
  Loader2,
  Home,
  Calendar,
  Clock,
  MapPin,
  User,
  AlertTriangle,
  RefreshCw,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  CalendarCheck,
  CalendarX,
  CalendarClock,
} from 'lucide-react'
import {
  cancelHomeVisit,
  checkHomeVisitConflicts,
  completeHomeVisitWithOutcomes,
  confirmHomeVisit,
  getMyHomeVisits,
  homeVisitSafetyCheckin,
  homeVisitSafetyCheckout,
  listEligibleSafetyBuddies,
  rescheduleHomeVisit,
  updateHomeVisit,
  type HomeVisitConflictCheck,
  type ParentHomeVisit,
} from '@/api/parent-onboarding-api'
import { useTranslation, getCurrentLocale } from '@/i18n'
import toast from 'react-hot-toast'
import { AdminShell } from '../components/shells/AdminShell'
import { parseDate } from '@/utils/format-utils'
import { getStatusConfig, todayLocalYMD } from './parentHomeVisitsHelpers'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'

function formatDate(d: string): string {
  const parsed = parseDate(d)
  if (!parsed) return '-'
  return parsed.toLocaleDateString(getCurrentLocale(), { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
}

const PURPOSE_LABELS: Record<string, string> = {
  intake: 'Intake Visit',
  resource_delivery: 'Resource Delivery',
  check_in: 'Check-in',
  service_enrollment: 'Service Enrollment',
  follow_up: 'Follow-up',
}

// Computes whether a visit is currently overdue on safety check-out
// independent of the backend `safety_overdue_flagged_at` stamp -- this
// lets the UI flag a visit as overdue immediately, even before the
// next scheduler tick has run.
function isSafetyOverdue(visit: ParentHomeVisit, now: Date = new Date()): boolean {
  if (!visit.safety_checkin_at) return false
  if (visit.safety_checkout_at) return false
  if (!visit.safety_checkout_due_at) return false
  return new Date(visit.safety_checkout_due_at).getTime() < now.getTime()
}

// Buttons + status line for the lone-worker safety mechanic. Gated by
// `home_visit_safety_enabled`; renders nothing when the flag is off.
// Kept inline (rather than a separate file) because it is tightly
// coupled to the visit-card layout and has no reuse outside this page.
export function HomeVisitSafetyPanel({
  visit,
  onUpdated,
}: {
  visit: ParentHomeVisit
  onUpdated?: () => void
}) {
  const { t } = useTranslation()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const queryClient = useQueryClient()
  const [duration, setDuration] = useState<number>(60)

  const enabled = isFeatureEnabled('home_visit_safety_enabled')

  // Lazy-load the eligible-buddy list only when the flag is on AND the
  // visit has not been checked in yet (buddy choice is locked at
  // check-in time). `enabled` gates both flag-off and post-checkin so
  // we don't burn a request when neither case needs the list.
  const buddyListQuery = useQuery({
    queryKey: ['eligible-safety-buddies'],
    queryFn: listEligibleSafetyBuddies,
    enabled: enabled && !visit.safety_checkin_at,
    staleTime: 60_000,
  })

  const buddyAssignMutation = useMutation({
    mutationFn: (newBuddyId: number | null) =>
      updateHomeVisit(visit.id, { safety_buddy_user_id: newBuddyId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-home-visits'] })
      toast.success(t('Safety buddy updated'))
      onUpdated?.()
    },
    onError: (err) => {
      Sentry.captureException(err)
      toast.error(t('Could not update safety buddy'))
    },
  })

  const checkinMutation = useMutation({
    mutationFn: () => homeVisitSafetyCheckin(visit.id, duration),
    onSuccess: (resp) => {
      if (resp.buddy_warning) {
        toast(resp.buddy_warning, { icon: '⚠', duration: 6000 })
      } else {
        toast.success(t('Safe arrival recorded'))
      }
      queryClient.invalidateQueries({ queryKey: ['my-home-visits'] })
      onUpdated?.()
    },
    onError: (err) => {
      Sentry.captureException(err)
      toast.error(t('Could not record check-in'))
    },
  })

  const checkoutMutation = useMutation({
    mutationFn: () => homeVisitSafetyCheckout(visit.id),
    onSuccess: () => {
      toast.success(t('Safe departure recorded'))
      queryClient.invalidateQueries({ queryKey: ['my-home-visits'] })
      onUpdated?.()
    },
    onError: (err) => {
      Sentry.captureException(err)
      toast.error(t('Could not record check-out'))
    },
  })

  if (!enabled) return null

  const checkedIn = !!visit.safety_checkin_at
  const checkedOut = !!visit.safety_checkout_at
  const overdue = isSafetyOverdue(visit)
  const buddies = buddyListQuery.data ?? []

  return (
    <div className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700">
      {!checkedIn && (
        <label className="flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
          <span>{t('Safety buddy')}</span>
          <select
            value={visit.safety_buddy_user_id ?? ''}
            onChange={(e) => {
              const v = e.target.value
              buddyAssignMutation.mutate(v === '' ? null : Number(v))
            }}
            disabled={buddyAssignMutation.isPending || buddyListQuery.isLoading}
            className="px-2 py-1 border border-lsc-border dark:border-earth-600 rounded text-sm bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            aria-label={t('Assign a safety buddy for this visit')}
          >
            <option value="">{t('— no buddy assigned —')}</option>
            {buddies.map((b) => (
              <option key={b.id} value={b.id}>{b.full_name}</option>
            ))}
          </select>
        </label>
      )}
      <div className="flex flex-wrap items-center gap-2">
        {!checkedIn && (
          <>
            <label className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              <span>{t('Expected duration (min)')}</span>
              <input
                type="number"
                min={5}
                max={480}
                value={duration}
                onChange={(e) => setDuration(Math.max(5, Math.min(480, Number(e.target.value) || 60)))}
                className="w-16 px-2 py-1 border border-lsc-border dark:border-earth-600 rounded text-sm bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                aria-label={t('Expected visit duration in minutes')}
              />
            </label>
            <button
              type="button"
              onClick={() => checkinMutation.mutate()}
              disabled={checkinMutation.isPending}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg bg-status-success-600 text-white hover:bg-status-success-700 disabled:opacity-60"
            >
              <ShieldCheck className="w-4 h-4" />
              {t('Mark Safe Arrival')}
            </button>
          </>
        )}
        {checkedIn && !checkedOut && (
          <button
            type="button"
            onClick={() => checkoutMutation.mutate()}
            disabled={checkoutMutation.isPending}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg bg-status-info-600 text-white hover:bg-status-info-700 disabled:opacity-60"
          >
            <ShieldCheck className="w-4 h-4" />
            {t('Mark Safe Departure')}
          </button>
        )}
        {checkedIn && (
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('parentOnboarding.homeVisits.arrived')}: {new Date(visit.safety_checkin_at as string).toLocaleTimeString()}
            {checkedOut && (
              <> · {t('parentOnboarding.homeVisits.departed')}: {new Date(visit.safety_checkout_at as string).toLocaleTimeString()}</>
            )}
          </span>
        )}
        {overdue && (
          <span
            role="status"
            aria-label={t('Safety check-out overdue')}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/40 dark:text-status-danger-200"
          >
            <ShieldAlert className="w-3.5 h-3.5" aria-hidden="true" />
            <span>{t('Check-out overdue')}</span>
          </span>
        )}
      </div>
    </div>
  )
}


// ----------------------------------------------------------------------------
// Status-mutation surface (home_visit_mutations_001)
//
// The HomeVisitActions row + three modal components below live inside this
// file rather than getting their own modules because they share state and
// query-invalidation patterns with the visit-card layout. They are not
// reused anywhere else; splitting them out would only buy file-count
// virtue, not testability.
// ----------------------------------------------------------------------------

const COMPLETE_RESOURCES: Array<{ value: string; label: string }> = [
  { value: 'books', label: 'Books / reading materials' },
  { value: 'diapers', label: 'Diapers / hygiene supplies' },
  { value: 'food', label: 'Food (referral or pantry box)' },
  { value: 'clothing', label: 'Clothing' },
  { value: 'service_help', label: 'Service application help' },
  { value: 'info_packet', label: 'Information packet' },
]

const CANCEL_REASONS: Array<{ value: string; labelKey: string; fallback: string }> = [
  { value: 'family_cancelled', labelKey: 'parentOnboarding.homeVisits.mutations.cancel.reasons.familyCancelled', fallback: 'Family canceled' },
  { value: 'family_no_show', labelKey: 'parentOnboarding.homeVisits.mutations.cancel.reasons.familyNoShow', fallback: 'Family no-show' },
  { value: 'staff_unavailable', labelKey: 'parentOnboarding.homeVisits.mutations.cancel.reasons.staffUnavailable', fallback: 'Staff unavailable' },
  { value: 'weather', labelKey: 'parentOnboarding.homeVisits.mutations.cancel.reasons.weather', fallback: 'Weather' },
  { value: 'other', labelKey: 'parentOnboarding.homeVisits.mutations.cancel.reasons.other', fallback: 'Other' },
]


// Inline action buttons (Confirm / Mark complete / Reschedule / Cancel).
// Hides actions that are invalid for the current status; never disables --
// per memory feedback_l30_nav_config_pattern: hide, don't disable.
export function HomeVisitActions({
  visit,
  onMutationDone,
}: {
  visit: ParentHomeVisit
  onMutationDone?: () => void
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [openModal, setOpenModal] = useState<null | 'complete' | 'reschedule' | 'cancel'>(null)

  const refetch = () => {
    queryClient.invalidateQueries({ queryKey: ['my-home-visits'] })
    onMutationDone?.()
  }

  const confirmMutation = useMutation({
    mutationFn: () => confirmHomeVisit(visit.id),
    // Optimistic: flip the row immediately, roll back on error.
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['my-home-visits'] })
      const prev = queryClient.getQueryData<{ visits: ParentHomeVisit[]; total: number }>(
        ['my-home-visits'],
      )
      if (prev) {
        queryClient.setQueryData(['my-home-visits'], {
          ...prev,
          visits: prev.visits.map((v) =>
            v.id === visit.id ? { ...v, status: 'confirmed' as const } : v,
          ),
        })
      }
      return { prev }
    },
    onError: (err, _vars, ctx) => {
      Sentry.captureException(err)
      if (ctx?.prev) queryClient.setQueryData(['my-home-visits'], ctx.prev)
      toast.error(t('parentOnboarding.homeVisits.mutations.errors.confirmFailed', 'Could not confirm visit'))
    },
    onSuccess: () => {
      toast.success(t('parentOnboarding.homeVisits.mutations.confirmedToast', 'Visit confirmed'))
    },
    onSettled: refetch,
  })

  // Only show actions that apply to the current status. Completed/cancelled/
  // rescheduled visits show no action row at all.
  const canConfirm = visit.status === 'scheduled'
  const canComplete = visit.status === 'scheduled' || visit.status === 'confirmed'
  const canReschedule = visit.status === 'scheduled' || visit.status === 'confirmed'
  const canCancel = visit.status === 'scheduled' || visit.status === 'confirmed'

  if (!canConfirm && !canComplete && !canReschedule && !canCancel) {
    return null
  }

  return (
    <>
      <div
        className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700 flex flex-wrap gap-2"
        role="group"
        aria-label={t('parentOnboarding.homeVisits.mutations.actionsAriaLabel', 'Visit actions')}
      >
        {canConfirm && (
          <button
            type="button"
            onClick={() => confirmMutation.mutate()}
            disabled={confirmMutation.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-status-success-600 text-white hover:bg-status-success-700 disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-status-success-500"
          >
            <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
            {t('parentOnboarding.homeVisits.mutations.confirm', 'Confirm')}
          </button>
        )}
        {canComplete && (
          <button
            type="button"
            onClick={() => setOpenModal('complete')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-status-info-600 text-white hover:bg-status-info-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-status-info-500"
          >
            <CalendarCheck className="w-4 h-4" aria-hidden="true" />
            {t('parentOnboarding.homeVisits.mutations.markComplete', 'Mark complete')}
          </button>
        )}
        {canReschedule && (
          <button
            type="button"
            onClick={() => setOpenModal('reschedule')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-600 hover:bg-lsc-border dark:hover:bg-earth-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose"
          >
            <CalendarClock className="w-4 h-4" aria-hidden="true" />
            {t('parentOnboarding.homeVisits.mutations.reschedule.submit', 'Reschedule')}
          </button>
        )}
        {canCancel && (
          <button
            type="button"
            onClick={() => setOpenModal('cancel')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-white dark:bg-earth-800 text-status-danger-700 dark:text-status-danger-300 border border-status-danger-300 dark:border-status-danger-700 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/30 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-status-danger-500"
          >
            <CalendarX className="w-4 h-4" aria-hidden="true" />
            {t('parentOnboarding.homeVisits.mutations.cancel.title', 'Cancel visit')}
          </button>
        )}
      </div>

      {openModal === 'complete' && (
        <CompleteVisitModal
          visit={visit}
          onClose={() => setOpenModal(null)}
          onDone={() => {
            setOpenModal(null)
            refetch()
          }}
        />
      )}
      {openModal === 'reschedule' && (
        <RescheduleVisitModal
          visit={visit}
          onClose={() => setOpenModal(null)}
          onDone={() => {
            setOpenModal(null)
            refetch()
          }}
        />
      )}
      {openModal === 'cancel' && (
        <CancelVisitModal
          visit={visit}
          onClose={() => setOpenModal(null)}
          onDone={() => {
            setOpenModal(null)
            refetch()
          }}
        />
      )}
    </>
  )
}


// ----- Modals ---------------------------------------------------------------
//
// L30 doesn't expose a primitive <Modal> component as of 2026-05-25, so each
// modal is a fixed-position overlay rendered into the same tree. We keep the
// focus trap minimal (auto-focus the first input on open, ESC to close) --
// real focus-trapping is documented as a TODO if these modals ever stack.
//

function ModalShell({
  titleId,
  title,
  onClose,
  children,
}: {
  titleId: string
  title: string
  onClose: () => void
  children: React.ReactNode
}) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div className="bg-white dark:bg-earth-900 rounded-xl shadow-lg max-w-lg w-full max-h-[90vh] overflow-y-auto p-6">
        <h2 id={titleId} className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          {title}
        </h2>
        {children}
      </div>
    </div>
  )
}

function CompleteVisitModal({
  visit,
  onClose,
  onDone,
}: {
  visit: ParentHomeVisit
  onClose: () => void
  onDone: () => void
}) {
  const { t } = useTranslation()
  const [outcomes, setOutcomes] = useState('')
  const [selectedResources, setSelectedResources] = useState<string[]>([])
  const [otherResource, setOtherResource] = useState('')
  const [followUpNeeded, setFollowUpNeeded] = useState(false)
  const [followUpDate, setFollowUpDate] = useState('')
  const [followUpNotes, setFollowUpNotes] = useState('')
  const [referrals, setReferrals] = useState('')

  const mutation = useMutation({
    mutationFn: () => {
      const resources = [...selectedResources]
      if (otherResource.trim()) resources.push(otherResource.trim())
      return completeHomeVisitWithOutcomes(visit.id, {
        outcomes: outcomes.trim(),
        resources_delivered: resources,
        follow_up_needed: followUpNeeded,
        follow_up_date: followUpNeeded && followUpDate ? followUpDate : undefined,
        follow_up_notes: followUpNotes.trim() || undefined,
        referrals: referrals
          .split(',')
          .map((r) => r.trim())
          .filter(Boolean),
      })
    },
    onSuccess: () => {
      toast.success(t('parentOnboarding.homeVisits.mutations.completedToast', 'Visit marked complete'))
      onDone()
    },
    onError: (err) => {
      Sentry.captureException(err)
      toast.error(t('parentOnboarding.homeVisits.mutations.errors.completeFailed', 'Could not save outcomes'))
    },
  })

  const outcomesMissing = !outcomes.trim()

  return (
    <ModalShell
      titleId={`complete-modal-${visit.id}`}
      title={t('parentOnboarding.homeVisits.mutations.complete.title', 'Complete visit')}
      onClose={onClose}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (outcomesMissing) return
          mutation.mutate()
        }}
        className="space-y-4"
      >
        <div>
          <label htmlFor={`outcomes-${visit.id}`} className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            {t('parentOnboarding.homeVisits.mutations.complete.outcomesLabel', 'Outcomes')}
            <span aria-hidden="true" className="text-status-danger-600 ml-1">*</span>
          </label>
          <textarea
            id={`outcomes-${visit.id}`}
            value={outcomes}
            onChange={(e) => setOutcomes(e.target.value)}
            maxLength={2000}
            rows={4}
            required
            autoFocus
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            placeholder={t('parentOnboarding.homeVisits.mutations.complete.outcomesPlaceholder', 'What happened? What was discussed?')}
            aria-required="true"
          />
        </div>

        <fieldset>
          <legend className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            {t('parentOnboarding.homeVisits.mutations.complete.resourcesLabel', 'Resources delivered')}
          </legend>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {COMPLETE_RESOURCES.map((r) => (
              <label key={r.value} className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                <input
                  type="checkbox"
                  checked={selectedResources.includes(r.label)}
                  onChange={(e) => {
                    setSelectedResources((prev) =>
                      e.target.checked
                        ? [...prev, r.label]
                        : prev.filter((x) => x !== r.label),
                    )
                  }}
                />
                {r.label}
              </label>
            ))}
          </div>
          <input
            type="text"
            value={otherResource}
            onChange={(e) => setOtherResource(e.target.value)}
            placeholder={t('parentOnboarding.homeVisits.mutations.complete.otherResourcePlaceholder', 'Other (free-form)')}
            className="mt-2 w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm"
            aria-label={t('parentOnboarding.homeVisits.mutations.complete.otherResourceAria', 'Other resource delivered')}
          />
        </fieldset>

        <div>
          <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
            <input
              type="checkbox"
              checked={followUpNeeded}
              onChange={(e) => setFollowUpNeeded(e.target.checked)}
            />
            {t('parentOnboarding.homeVisits.mutations.complete.followUpToggle', 'Follow-up needed')}
          </label>
          {followUpNeeded && (
            <div className="mt-2 space-y-2 pl-6">
              <label className="block text-sm">
                <span className="block text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  {t('parentOnboarding.homeVisits.mutations.complete.followUpDate', 'Follow-up date')}
                </span>
                <input
                  type="date"
                  value={followUpDate}
                  onChange={(e) => setFollowUpDate(e.target.value)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </label>
              <label className="block text-sm">
                <span className="block text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  {t('parentOnboarding.homeVisits.mutations.complete.followUpNotes', 'Follow-up notes')}
                </span>
                <textarea
                  value={followUpNotes}
                  onChange={(e) => setFollowUpNotes(e.target.value)}
                  rows={2}
                  maxLength={2000}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </label>
            </div>
          )}
        </div>

        <div>
          <label htmlFor={`referrals-${visit.id}`} className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            {t('parentOnboarding.homeVisits.mutations.complete.referralsLabel', 'Referrals made')}
          </label>
          <input
            id={`referrals-${visit.id}`}
            type="text"
            value={referrals}
            onChange={(e) => setReferrals(e.target.value)}
            placeholder={t('parentOnboarding.homeVisits.mutations.complete.referralsPlaceholder', 'e.g. WIC office, school counselor')}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm"
          />
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">
            {t('parentOnboarding.homeVisits.mutations.complete.referralsHelp', 'Separate multiple referrals with commas')}
          </p>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          >
            {t('common.cancel', 'Cancel')}
          </button>
          <button
            type="submit"
            disabled={outcomesMissing || mutation.isPending}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-status-info-600 text-white hover:bg-status-info-700 disabled:opacity-60"
          >
            {mutation.isPending
              ? t('common.saving', 'Saving...')
              : t('parentOnboarding.homeVisits.mutations.complete.submit', 'Save outcomes')}
          </button>
        </div>
      </form>
    </ModalShell>
  )
}


function RescheduleVisitModal({
  visit,
  onClose,
  onDone,
}: {
  visit: ParentHomeVisit
  onClose: () => void
  onDone: () => void
}) {
  const { t } = useTranslation()
  const [newDate, setNewDate] = useState('')
  const [newTime, setNewTime] = useState(visit.scheduled_time || '10:00')
  const [duration, setDuration] = useState<number>(60)
  const [reason, setReason] = useState('')
  const [conflicts, setConflicts] = useState<HomeVisitConflictCheck | null>(null)

  // Debounced conflict check (300ms) keyed on visitor + date. State writes
  // happen inside the timeout (or its abort cleanup), not synchronously in
  // the effect body -- the eslint rule react-hooks/set-state-in-effect bans
  // the latter to prevent cascading renders.
  useEffect(() => {
    let cancelled = false
    if (!newDate || !visit.visitor_id) {
      const t0 = setTimeout(() => {
        if (!cancelled) setConflicts(null)
      }, 0)
      return () => {
        cancelled = true
        clearTimeout(t0)
      }
    }
    const handle = setTimeout(async () => {
      try {
        const result = await checkHomeVisitConflicts({
          visitor_id: visit.visitor_id,
          date: newDate,
          exclude_visit_id: visit.id,
        })
        if (!cancelled) setConflicts(result)
      } catch (err) {
        Sentry.captureException(err)
      }
    }, 300)
    return () => {
      cancelled = true
      clearTimeout(handle)
    }
  }, [newDate, visit.visitor_id, visit.id])

  const mutation = useMutation({
    mutationFn: () =>
      rescheduleHomeVisit(visit.id, {
        new_scheduled_date: newDate,
        new_scheduled_time: newTime || undefined,
        duration_minutes: duration,
        reason: reason.trim(),
      }),
    onSuccess: () => {
      toast.success(t('parentOnboarding.homeVisits.mutations.rescheduledToast', 'Visit rescheduled'))
      onDone()
    },
    onError: (err) => {
      Sentry.captureException(err)
      toast.error(t('parentOnboarding.homeVisits.mutations.errors.rescheduleFailed', 'Could not reschedule visit'))
    },
  })

  const disabled = !newDate || !reason.trim() || mutation.isPending

  // Min/max date constraints: today + 1 to today + 90 days. Memo'd once
  // so the dependency array stays stable across renders.
  const { minDate, maxDate } = useMemo(() => {
    const now = new Date()
    const min = new Date(now)
    min.setDate(min.getDate() + 1)
    const max = new Date(now)
    max.setDate(max.getDate() + 90)
    return {
      minDate: min.toISOString().slice(0, 10),
      maxDate: max.toISOString().slice(0, 10),
    }
  }, [])

  return (
    <ModalShell
      titleId={`reschedule-modal-${visit.id}`}
      title={t('parentOnboarding.homeVisits.mutations.reschedule.title', 'Reschedule visit')}
      onClose={onClose}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (!disabled) mutation.mutate()
        }}
        className="space-y-4"
      >
        <div className="grid grid-cols-2 gap-3">
          <label className="block text-sm">
            <span className="block text-lsc-dark dark:text-lsc-cream font-medium mb-1">
              {t('parentOnboarding.homeVisits.mutations.reschedule.newDate', 'New date')}
              <span aria-hidden="true" className="text-status-danger-600 ml-1">*</span>
            </span>
            <input
              type="date"
              value={newDate}
              onChange={(e) => setNewDate(e.target.value)}
              min={minDate}
              max={maxDate}
              required
              autoFocus
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </label>
          <label className="block text-sm">
            <span className="block text-lsc-dark dark:text-lsc-cream font-medium mb-1">
              {t('parentOnboarding.homeVisits.mutations.reschedule.newTime', 'New time')}
            </span>
            <input
              type="time"
              value={newTime}
              onChange={(e) => setNewTime(e.target.value)}
              step={900}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </label>
        </div>

        <label className="block text-sm">
          <span className="block text-lsc-dark dark:text-lsc-cream font-medium mb-1">
            {t('parentOnboarding.homeVisits.mutations.reschedule.duration', 'Duration (minutes)')}
          </span>
          <input
            type="number"
            min={5}
            max={480}
            value={duration}
            onChange={(e) => setDuration(Math.max(5, Math.min(480, Number(e.target.value) || 60)))}
            className="w-32 px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
          />
        </label>

        {conflicts?.has_conflict && (
          <div
            role="status"
            aria-live="polite"
            className="text-sm bg-status-warning-50 dark:bg-status-warning-900/30 border border-status-warning-300 dark:border-status-warning-700 rounded-lg px-3 py-2 text-status-warning-800 dark:text-status-warning-200"
          >
            {t(
              'parentOnboarding.homeVisits.mutations.reschedule.conflictWarning',
              'Heads up: this visitor has {{count}} other visit on this day',
            ).replace('{{count}}', String(conflicts.conflicting_visits.length))}
          </div>
        )}

        <label className="block text-sm">
          <span className="block text-lsc-dark dark:text-lsc-cream font-medium mb-1">
            {t('parentOnboarding.homeVisits.mutations.reschedule.reason', 'Reason for reschedule')}
            <span aria-hidden="true" className="text-status-danger-600 ml-1">*</span>
          </span>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            maxLength={1000}
            required
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            aria-required="true"
          />
        </label>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          >
            {t('common.cancel', 'Cancel')}
          </button>
          <button
            type="submit"
            disabled={disabled}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-60"
          >
            {mutation.isPending
              ? t('common.saving', 'Saving...')
              : t('parentOnboarding.homeVisits.mutations.reschedule.submit', 'Reschedule')}
          </button>
        </div>
      </form>
    </ModalShell>
  )
}


function CancelVisitModal({
  visit,
  onClose,
  onDone,
}: {
  visit: ParentHomeVisit
  onClose: () => void
  onDone: () => void
}) {
  const { t } = useTranslation()
  const [reasonValue, setReasonValue] = useState<string>('family_cancelled')
  const [otherText, setOtherText] = useState('')
  const [notifyAck, setNotifyAck] = useState(false)

  const finalReason =
    reasonValue === 'other'
      ? otherText.trim()
      : CANCEL_REASONS.find((r) => r.value === reasonValue)?.fallback ?? reasonValue

  const mutation = useMutation({
    mutationFn: () =>
      cancelHomeVisit(visit.id, {
        cancelled_reason: finalReason,
        notify_acknowledged: notifyAck,
      }),
    onSuccess: () => {
      toast.success(t('parentOnboarding.homeVisits.mutations.cancelledToast', 'Visit cancelled'))
      onDone()
    },
    onError: (err) => {
      Sentry.captureException(err)
      toast.error(t('parentOnboarding.homeVisits.mutations.errors.cancelFailed', 'Could not cancel visit'))
    },
  })

  const disabled =
    !notifyAck ||
    (reasonValue === 'other' && !otherText.trim()) ||
    mutation.isPending

  return (
    <ModalShell
      titleId={`cancel-modal-${visit.id}`}
      title={t('parentOnboarding.homeVisits.mutations.cancel.title', 'Cancel visit')}
      onClose={onClose}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (!disabled) mutation.mutate()
        }}
        className="space-y-4"
      >
        <fieldset>
          <legend className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            {t('parentOnboarding.homeVisits.mutations.cancel.reasonLabel', 'Reason')}
          </legend>
          <div className="space-y-2">
            {CANCEL_REASONS.map((r) => (
              <label key={r.value} className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                <input
                  type="radio"
                  name={`cancel-reason-${visit.id}`}
                  value={r.value}
                  checked={reasonValue === r.value}
                  onChange={() => setReasonValue(r.value)}
                />
                {t(r.labelKey, r.fallback)}
              </label>
            ))}
          </div>
        </fieldset>

        {reasonValue === 'other' && (
          <label className="block text-sm">
            <span className="block text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              {t('parentOnboarding.homeVisits.mutations.cancel.reasonOther', 'Specify reason')}
              <span aria-hidden="true" className="text-status-danger-600 ml-1">*</span>
            </span>
            <input
              type="text"
              value={otherText}
              onChange={(e) => setOtherText(e.target.value)}
              maxLength={1000}
              required
              autoFocus
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </label>
        )}

        <label className="flex items-start gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
          <input
            type="checkbox"
            checked={notifyAck}
            onChange={(e) => setNotifyAck(e.target.checked)}
            className="mt-0.5"
            aria-required="true"
          />
          <span>
            {t(
              'parentOnboarding.homeVisits.mutations.cancel.notifyCheck',
              'I have notified the family or will within 1 hour',
            )}
          </span>
        </label>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            autoFocus
            className="px-4 py-2 text-sm font-medium rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          >
            {t('common.cancel', 'Cancel')}
          </button>
          <button
            type="submit"
            disabled={disabled}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-status-danger-600 text-white hover:bg-status-danger-700 disabled:opacity-60"
          >
            {mutation.isPending
              ? t('common.saving', 'Saving...')
              : t('parentOnboarding.homeVisits.mutations.cancel.confirm', 'Cancel this visit')}
          </button>
        </div>
      </form>
    </ModalShell>
  )
}


export default function ParentHomeVisitsPage() {
  const { t } = useTranslation()

  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['my-home-visits'],
    queryFn: () => getMyHomeVisits({ limit: 50 }),
  })

  if (error) {
    Sentry.captureException(error)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6 text-center">
          <AlertTriangle className="w-8 h-8 text-status-danger-500 mx-auto mb-2" />
          <p className="text-status-danger-700 dark:text-status-danger-300">{t('parentOnboarding.homeVisits.failedToLoad', 'Failed to load home visits')}</p>
          <button
            onClick={() => refetch()}
            className="mt-3 px-4 py-2 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 rounded-lg text-sm"
          >
            {t('common.retry', 'Retry')}
          </button>
        </div>
      </div>
    )
  }

  const visits = data?.visits ?? []

  // `scheduled_date` is a bare YYYY-MM-DD column representing the local
  // calendar day. Compare against today in the viewer's local tz, not UTC,
  // so a 5pm Pacific page load doesn't push tomorrow into "Past".
  const today = todayLocalYMD()
  const upcomingVisits = visits.filter(
    (v: ParentHomeVisit) => v.scheduled_date >= today && v.status !== 'completed' && v.status !== 'cancelled'
  )
  const pastVisits = visits.filter(
    (v: ParentHomeVisit) => v.scheduled_date < today || v.status === 'completed' || v.status === 'cancelled'
  )

  return (
    <AdminShell title="Parent Home Visits">
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {t('parentOnboarding.homeVisits.title', 'Home Visits')}
          </h1>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {t('parentOnboarding.homeVisits.listSubtitle', 'View your scheduled and past home visits.')}
          </p>
        </div>
        <button
          onClick={() => {
            refetch()
            toast.success(t('parentOnboarding.homeVisits.refreshedToast', 'Refreshed'))
          }}
          className="flex items-center gap-2 px-3 py-2 text-sm bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-border dark:hover:bg-earth-600 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          {t('common.refresh', 'Refresh')}
        </button>
      </div>

      {visits.length === 0 ? (
        <div className="text-center py-12">
          <Home className="w-12 h-12 text-lsc-dark/20 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/60">{t('parentOnboarding.homeVisits.noVisitsScheduled', 'No home visits scheduled')}</p>
        </div>
      ) : (
        <>
          {/* Upcoming Visits */}
          {upcomingVisits.length > 0 && (
            <div>
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                {t('parentOnboarding.dashboard.upcomingVisitsLabel', 'Upcoming Visits')}
              </h2>
              <div className="space-y-3">
                {upcomingVisits.map((visit: ParentHomeVisit) => {
                  const config = getStatusConfig(visit.status)
                  const statusLabel = t(`home_visit.status.${visit.status}`)
                  return (
                    <div
                      key={visit.id}
                      className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                            {t(PURPOSE_LABELS[visit.purpose] ?? visit.purpose)}
                          </h3>
                          <span
                            role="status"
                            aria-label={statusLabel}
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium mt-1 ${config.color}`}
                          >
                            {config.icon}
                            <span aria-hidden="true" className="font-mono text-[0.85em] leading-none">{config.monoCue}</span>
                            <span>{statusLabel}</span>
                          </span>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" />
                          {formatDate(visit.scheduled_date)}
                        </div>
                        {visit.scheduled_time && (
                          <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" />
                            {visit.scheduled_time}
                            {visit.duration_minutes ? ` (${visit.duration_minutes} min)` : ''}
                          </div>
                        )}
                        {visit.visitor_name && (
                          <div className="flex items-center gap-2">
                            <User className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" />
                            {visit.visitor_name}
                          </div>
                        )}
                        {visit.address && (
                          <div className="flex items-center gap-2">
                            <MapPin className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" />
                            {visit.address}
                          </div>
                        )}
                      </div>

                      {visit.notes && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-3 italic">
                          {visit.notes}
                        </p>
                      )}

                      {visit.rescheduled_to && (
                        <p className="text-xs text-status-warning-600 dark:text-status-warning-400 mt-2">
                          {t('parentOnboarding.homeVisits.rescheduledTo', 'Rescheduled to')}: {formatDate(visit.rescheduled_to)}
                        </p>
                      )}

                      <HomeVisitActions visit={visit} />
                      <HomeVisitSafetyPanel visit={visit} />
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Past Visits */}
          {pastVisits.length > 0 && (
            <div>
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                {t('parentOnboarding.homeVisits.pastVisits', 'Past Visits')}
              </h2>
              <div className="space-y-3">
                {pastVisits.map((visit: ParentHomeVisit) => {
                  const config = getStatusConfig(visit.status)
                  const statusLabel = t(`home_visit.status.${visit.status}`)
                  return (
                    <div
                      key={visit.id}
                      className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4 opacity-80"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div>
                            <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                              {t(PURPOSE_LABELS[visit.purpose] ?? visit.purpose)}
                            </h3>
                            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                              {formatDate(visit.scheduled_date)}
                              {visit.visitor_name ? ` - ${visit.visitor_name}` : ''}
                            </p>
                          </div>
                        </div>
                        <span
                          role="status"
                          aria-label={statusLabel}
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.color}`}
                        >
                          {config.icon}
                          <span aria-hidden="true" className="font-mono text-[0.85em] leading-none">{config.monoCue}</span>
                          <span>{statusLabel}</span>
                        </span>
                      </div>
                      {visit.outcomes && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                          <span className="font-medium">{t('parentOnboarding.homeVisits.outcomes', 'Outcomes')}:</span> {visit.outcomes}
                        </p>
                      )}
                      {visit.resources_delivered && visit.resources_delivered.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {visit.resources_delivered.map((r, i) => (
                            // `resources_delivered` is a `string[]` payload
                            // without per-row stable IDs. Pair the resource
                            // text with visit.id so React doesn't re-key on
                            // index alone if the array is reordered.
                            <span
                              key={`${visit.id}-${r}-${i}`}
                              className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                            >
                              {r}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
    </AdminShell>
  )
}
