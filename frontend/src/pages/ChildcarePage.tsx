/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useId, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as Sentry from "@/lib/sentry-lazy"
import {
  Loader2,
  Baby,
  Calendar,
  Clock,
  MapPin,
  Users,
  AlertTriangle,
  CheckCircle,
  Plus,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  createChildcareSession,
  listChildcareSessions,
  registerForChildcare,
  type ChildcareRegistration,
  type ChildcareSession,
  type ChildcareSessionStatus,
} from '@/api/parent-onboarding-api'
import { listBranches, type Branch } from '@/api/branch-api'
import { useTranslation, useLanguage } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import StaffChildcareCheckoutModal from '../components/staff/parent-onboarding/StaffChildcareCheckoutModal'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { useAuth } from '@/contexts/AuthContext'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { parseDate } from '@/utils/format-utils'
import { StaffRosterPanel } from '../components/staff/parent-onboarding/StaffRosterPanel'
import { NoShowModal } from '../components/staff/parent-onboarding/NoShowModal'

// Today's date as YYYY-MM-DD (local, no UTC drift). Used as the default
// for the "From" filter and as the minimum date on Create-session.
function todayLocalISO(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// All valid status values. Source of truth: ChildcareSessionStatus union in
// parent-onboarding-api.ts. Order matters for the pill-group keyboard nav.
const STATUS_OPTIONS: readonly ChildcareSessionStatus[] = [
  'available',
  'full',
  'in_progress',
  'completed',
  'cancelled',
] as const

function isValidStatus(v: string | null): v is ChildcareSessionStatus {
  return v != null && (STATUS_OPTIONS as readonly string[]).includes(v)
}

function formatDate(d: string, locale: string): string {
  const parsed = parseDate(d)
  if (!parsed) return '-'
  try {
    return parsed.toLocaleDateString(locale, { weekday: 'short', month: 'short', day: 'numeric' })
  } catch {
    // Fallback if locale tag is unsupported by the runtime
    return parsed.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
  }
}


function SessionStatusBadge({ status }: { status: ChildcareSessionStatus }) {
  const base = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium'
  const colors: Record<ChildcareSessionStatus, string> = {
    available: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
    full: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    in_progress: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-400',
    completed: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
    cancelled: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
  }
  return (
    <span className={`${base} ${colors[status]}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

// Fields that can produce inline validation errors in the register-modal.
type FieldKey =
  | 'childName'
  | 'childAgeYears'
  | 'emergencyContactName'
  | 'emergencyContactPhone'
type FieldErrors = Partial<Record<FieldKey, string>>

// Backend caps `child_age_months` at 60 (5y). Mirror that on the input so
// validation surfaces inline instead of as a 422 toast.
const MAX_CHILD_AGE_YEARS = 5

export default function ChildcarePage() {
  const { t } = useTranslation()
  const { language } = useLanguage()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { isFeatureEnabled } = useOrganizationFeatures()

  const isStaff = !!user && ['staff', 'library_admin', 'admin', 'super_admin', 'director'].includes(user.role)
  // Library-admin gating mirrors the backend's `require_library_admin`
  // dependency, which is STRICT -- only LIBRARY_ADMIN. ADMIN /
  // SUPER_ADMIN / DIRECTOR do NOT pass the backend check. This is by
  // design; see app/api/v1/dependencies.py and the PATCH route's NOTE
  // comment. Backend re-enforces -- the UI just hides the affordance to
  // match.
  const isLibraryAdmin = user?.role === 'library_admin'
  const pickupFlagOn = isFeatureEnabled('pickup_authorization_enabled')
  // Roster (check-in / no-show) is independent of pickup_authorization;
  // staff need check-in capability whether or not the library has opted
  // into the authorized-pickup workflow. The checkout button inside the
  // roster respects pickupFlagOn separately.
  const showStaffRoster = isStaff

  // Staff: per-session roster expansion + checkout-modal target + no-show
  // modal target.
  const [expandedRosterSessionId, setExpandedRosterSessionId] = useState<number | null>(null)
  const [checkoutTarget, setCheckoutTarget] = useState<ChildcareRegistration | null>(null)
  const [noShowTarget, setNoShowTarget] = useState<ChildcareRegistration | null>(null)

  // ------------------------------------------------------------------
  // URL-synced filter state.
  //
  // Each filter is a single string in the URL ?status=... &branch_id=...
  // &from_date=... &to_date=... -- matches the established L30 catalog
  // sidebar pattern (single-select-string per facet; multi-select would
  // need a sidebar-wide refactor, out of scope for this PR; see memory
  // `feedback_l30_sidebar_filters_single_select`).
  //
  // Defaults: status = `available`, from_date = today. Branch and to_date
  // start unset ("all branches", no upper bound).
  // ------------------------------------------------------------------
  const [searchParams, setSearchParams] = useSearchParams()
  const filterStatus: ChildcareSessionStatus | '' = (() => {
    const v = searchParams.get('status')
    if (v === '') return ''
    if (isValidStatus(v)) return v
    return 'available'
  })()
  const filterBranchIdRaw = searchParams.get('branch_id') ?? ''
  const filterBranchId: number | '' =
    /^\d+$/.test(filterBranchIdRaw) ? Number(filterBranchIdRaw) : ''
  const filterFromDate = searchParams.get('from_date') ?? todayLocalISO()
  const filterToDate = searchParams.get('to_date') ?? ''

  function updateFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams)
    if (value === '') {
      next.delete(key)
    } else {
      next.set(key, value)
    }
    setSearchParams(next, { replace: true })
  }

  function resetFilters() {
    setSearchParams({}, { replace: true })
  }

  // ------------------------------------------------------------------
  // Create-session modal state (library_admin only).
  // ------------------------------------------------------------------
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createBranchId, setCreateBranchId] = useState<string>('')
  const [createRoomId, setCreateRoomId] = useState<string>('')
  const [createStaffId, setCreateStaffId] = useState<string>('')
  const [createDate, setCreateDate] = useState<string>(todayLocalISO())
  const [createStartTime, setCreateStartTime] = useState<string>('10:00')
  const [createEndTime, setCreateEndTime] = useState<string>('11:30')
  const [createMaxChildren, setCreateMaxChildren] = useState<string>('6')
  const [createAgeMin, setCreateAgeMin] = useState<string>('0')
  const [createAgeMax, setCreateAgeMax] = useState<string>('60')
  const [createError, setCreateError] = useState<string>('')

  const [showRegisterModal, setShowRegisterModal] = useState(false)
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)
  const [childName, setChildName] = useState('')
  // User-facing units: years. Converted to months at POST time to match
  // backend `child_age_months` (0-60).
  const [childAgeYears, setChildAgeYears] = useState('')
  const [specialNeeds, setSpecialNeeds] = useState('')
  const [emergencyContactName, setEmergencyContactName] = useState('')
  const [emergencyContactPhone, setEmergencyContactPhone] = useState('')
  const [allergies, setAllergies] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})

  // useId() gives a stable, SSR-safe id per render; suffixes give us one
  // per input. This keeps label htmlFor / input id pairs unique even if the
  // page is ever mounted twice.
  const formId = useId()
  const ids = {
    childName: `${formId}-child-name`,
    childAgeYears: `${formId}-child-age-years`,
    emergencyContactName: `${formId}-ec-name`,
    emergencyContactPhone: `${formId}-ec-phone`,
    allergies: `${formId}-allergies`,
    specialNeeds: `${formId}-special-needs`,
    modalTitle: `${formId}-modal-title`,
  }

  // Sessions list is keyed on the URL-synced filters so react-query
  // refetches automatically when the user touches a filter.
  const {
    data,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['childcare-sessions', filterStatus, filterBranchId, filterFromDate, filterToDate],
    queryFn: () =>
      listChildcareSessions({
        ...(filterStatus !== '' && { status: filterStatus }),
        ...(filterBranchId !== '' && { branch_id: filterBranchId }),
        ...(filterFromDate !== '' && { from_date: filterFromDate }),
        ...(filterToDate !== '' && { to_date: filterToDate }),
        limit: 50,
      }),
  })

  // Branches: one query, cached. Used by both the filter dropdown and the
  // create-session modal. Falls back to []; the UI degrades gracefully to
  // a numeric input on either an empty list or a failed request (the
  // backend `childcare_sessions.branch_id` column has no FK enforcement
  // anyway -- see app/models/parent_onboarding.py).
  const { data: branchesData } = useQuery({
    queryKey: ['branches', { active_only: true }],
    queryFn: () => listBranches({ active_only: true }),
    // Branches don't change in a session-mgmt-modal lifetime; long stale.
    staleTime: 5 * 60 * 1000,
  })
  const branches: Branch[] = useMemo(() => branchesData ?? [], [branchesData])
  const branchNameById: Map<number, string> = useMemo(() => {
    const m = new Map<number, string>()
    for (const b of branches) m.set(b.id, b.short_name || b.name || `Branch ${b.id}`)
    return m
  }, [branches])

  const createMutation = useMutation({
    mutationFn: createChildcareSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['childcare-sessions'] })
      toast.success(t('parentOnboarding.childcare.sessions.create.createdToast'))
      setShowCreateModal(false)
      setCreateError('')
    },
    onError: (err) => {
      Sentry.captureException(err)
      // Surface a translated, generic message; backend 422 details vary
      // (Pydantic message, capacity-floor message, etc.) and aren't worth
      // mapping here in v1.
      setCreateError(t('parentOnboarding.childcare.sessions.create.errorGeneric'))
    },
  })

  function handleCreateSubmit() {
    setCreateError('')
    // Required: branch_id + date + start + end + max_children.
    if (createBranchId === '' || !/^\d+$/.test(createBranchId)) {
      setCreateError(t('forms.requiredField'))
      return
    }
    if (!createDate || !createStartTime || !createEndTime) {
      setCreateError(t('forms.requiredField'))
      return
    }
    // End must be strictly after start. Lexicographic compare on HH:MM is
    // correct because both sides are zero-padded same-day strings.
    if (createEndTime <= createStartTime) {
      setCreateError(t('parentOnboarding.childcare.sessions.create.errorEndBeforeStart'))
      return
    }
    const ageMinN = Number(createAgeMin || '0')
    const ageMaxN = Number(createAgeMax || '60')
    if (ageMinN > ageMaxN) {
      setCreateError(t('parentOnboarding.childcare.sessions.create.errorAgeMinGtMax'))
      return
    }
    const maxN = Number(createMaxChildren || '6')

    createMutation.mutate({
      branch_id: Number(createBranchId),
      ...(createRoomId !== '' && { room_id: Number(createRoomId) }),
      ...(createStaffId !== '' && { staff_id: Number(createStaffId) }),
      date: createDate,
      start_time: createStartTime,
      end_time: createEndTime,
      max_children: maxN,
      age_range_min_months: ageMinN,
      age_range_max_months: ageMaxN,
    })
  }

  const registerMutation = useMutation({
    mutationFn: (params: { sessionId: number; data: Parameters<typeof registerForChildcare>[1] }) =>
      registerForChildcare(params.sessionId, params.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['childcare-sessions'] })
      toast.success(t('Registration successful!'))
      resetForm()
    },
    onError: (err) => {
      Sentry.captureException(err)
      toast.error(t('Failed to register. Please try again.'))
    },
  })

  function resetForm() {
    setShowRegisterModal(false)
    setSelectedSessionId(null)
    setChildName('')
    setChildAgeYears('')
    setSpecialNeeds('')
    setEmergencyContactName('')
    setEmergencyContactPhone('')
    setAllergies('')
    setFieldErrors({})
  }

  function validate(): FieldErrors {
    const errs: FieldErrors = {}
    const requiredMsg = t('forms.requiredField')
    if (!childName.trim()) errs.childName = requiredMsg
    const ageRaw = childAgeYears.trim()
    if (!ageRaw) {
      errs.childAgeYears = requiredMsg
    } else if (!/^\d+$/.test(ageRaw)) {
      errs.childAgeYears = t('forms.invalidFormat')
    } else {
      const years = Number(ageRaw)
      if (years > MAX_CHILD_AGE_YEARS) {
        errs.childAgeYears = t('parentOnboarding.childcare.ageOutOfRange', {
          defaultValue: 'Childcare is available for children up to {max} years old.',
          max: MAX_CHILD_AGE_YEARS,
        })
      }
    }
    if (!emergencyContactName.trim()) errs.emergencyContactName = requiredMsg
    if (!emergencyContactPhone.trim()) errs.emergencyContactPhone = requiredMsg
    return errs
  }

  function handleRegister() {
    if (!selectedSessionId) return
    const errs = validate()
    setFieldErrors(errs)
    if (Object.keys(errs).length > 0) {
      // Keep the toast as a backup signal for screen-reader users who
      // dismissed inline errors and for sighted-but-distracted patrons.
      toast.error(t('Please fill in all required fields'))
      return
    }
    // Backend wants `child_age_months` (0-60). UI collects years; convert
    // at the boundary so the schema stays authoritative.
    const childAgeMonths = Number(childAgeYears) * 12
    // `allergies` has no dedicated backend field. Roll it into
    // `special_needs_notes` so the user-entered text is preserved without
    // a backend schema change. (See PR audit notes.)
    const notesParts = [
      allergies.trim() ? `Allergies: ${allergies.trim()}` : '',
      specialNeeds.trim(),
    ].filter(Boolean)
    const specialNeedsNotes = notesParts.join('\n').trim()
    registerMutation.mutate({
      sessionId: selectedSessionId,
      data: {
        child_name: childName,
        child_age_months: childAgeMonths,
        ...(specialNeedsNotes && { special_needs_notes: specialNeedsNotes }),
        emergency_contact_name: emergencyContactName,
        emergency_contact_phone: emergencyContactPhone,
      },
    })
  }

  function openRegister(sessionId: number) {
    setSelectedSessionId(sessionId)
    setShowRegisterModal(true)
  }

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
          <p className="text-status-danger-700 dark:text-status-danger-300">{t('Failed to load childcare sessions')}</p>
        </div>
      </div>
    )
  }

  const sessions = data?.sessions ?? []
  const selectedSession = sessions.find((s: ChildcareSession) => s.id === selectedSessionId) ?? null

  // Compose a human-readable label for a session card. There is NO `name`
  // column on the backend, so we derive one from "<branch> · <date>".
  // Falls back to "Childcare session #<id>" if the branch isn't found in
  // the loaded branches list (e.g. branches API failed).
  function sessionLabel(s: ChildcareSession): string {
    const branchName = branchNameById.get(s.branch_id)
    const datePart = formatDate(s.date, language)
    if (branchName) return `${branchName} | ${datePart}`
    return `${t('parentOnboarding.childcare.pageTitle')} #${s.id}`
  }

  // Are any filters non-default? Drives the "no sessions match filters"
  // vs "no sessions at all" empty-state copy.
  const hasActiveFilters =
    filterStatus !== 'available' ||
    filterBranchId !== '' ||
    filterFromDate !== todayLocalISO() ||
    filterToDate !== ''

  // sr-only word for the visual "*" indicator. Reuses contact.requiredSrLabel
  // ("required" in en, already translated in all 7 locales) to avoid adding
  // a parallel key. If a shared forms.requiredSrLabel is ever added, swap to it.
  const requiredSrLabel = t('contact.requiredSrLabel')

  return (
    <AdminShell title="Childcare Services">
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('parentOnboarding.childcare.pageTitle')}
        </h1>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
          {t('parentOnboarding.childcare.pageSubtitle')}
        </p>
      </div>

      {/* Filter row: status pills, branch select, date range, reset, new-session button */}
      <div
        className="flex flex-wrap items-end gap-3 p-4 bg-lsc-cream/40 dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700"
        data-testid="childcare-filters"
      >
        {/* Status pill group */}
        <fieldset className="flex flex-col gap-1">
          <legend className="text-xs font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            {t('parentOnboarding.childcare.sessions.filters.statusLabel')}
          </legend>
          <div role="radiogroup" aria-label={t('parentOnboarding.childcare.sessions.filters.statusLabel')} className="flex flex-wrap gap-1">
            <button
              type="button"
              role="radio"
              aria-checked={filterStatus === ''}
              onClick={() => updateFilter('status', '')}
              data-testid="status-pill-all"
              className={`px-2 py-1 text-xs rounded-full border ${
                filterStatus === ''
                  ? 'bg-lsc-rose text-white border-lsc-rose'
                  : 'bg-lsc-white dark:bg-earth-700 border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream'
              }`}
            >
              {t('parentOnboarding.childcare.sessions.filters.allStatuses')}
            </button>
            {STATUS_OPTIONS.map((s) => (
              <button
                key={s}
                type="button"
                role="radio"
                aria-checked={filterStatus === s}
                onClick={() => updateFilter('status', s)}
                data-testid={`status-pill-${s}`}
                className={`px-2 py-1 text-xs rounded-full border ${
                  filterStatus === s
                    ? 'bg-lsc-rose text-white border-lsc-rose'
                    : 'bg-lsc-white dark:bg-earth-700 border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream'
                }`}
              >
                {s.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </fieldset>

        {/* Branch select */}
        <div className="flex flex-col gap-1">
          <label
            htmlFor="childcare-branch-filter"
            className="text-xs font-medium text-lsc-dark dark:text-lsc-cream"
          >
            {t('parentOnboarding.childcare.sessions.filters.branchLabel')}
          </label>
          <select
            id="childcare-branch-filter"
            value={filterBranchId === '' ? '' : String(filterBranchId)}
            onChange={(e) => updateFilter('branch_id', e.target.value)}
            className="text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">{t('parentOnboarding.childcare.sessions.filters.allBranches')}</option>
            {branches.map((b) => (
              <option key={b.id} value={b.id}>
                {b.short_name || b.name}
              </option>
            ))}
          </select>
        </div>

        {/* From date */}
        <div className="flex flex-col gap-1">
          <label
            htmlFor="childcare-from-date"
            className="text-xs font-medium text-lsc-dark dark:text-lsc-cream"
          >
            {t('parentOnboarding.childcare.sessions.filters.fromDateLabel')}
          </label>
          <input
            id="childcare-from-date"
            type="date"
            value={filterFromDate}
            aria-describedby="childcare-date-help"
            onChange={(e) => updateFilter('from_date', e.target.value)}
            className="text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          />
        </div>

        {/* To date */}
        <div className="flex flex-col gap-1">
          <label
            htmlFor="childcare-to-date"
            className="text-xs font-medium text-lsc-dark dark:text-lsc-cream"
          >
            {t('parentOnboarding.childcare.sessions.filters.toDateLabel')}
          </label>
          <input
            id="childcare-to-date"
            type="date"
            value={filterToDate}
            aria-describedby="childcare-date-help"
            onChange={(e) => updateFilter('to_date', e.target.value)}
            className="text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          />
        </div>

        {/* Hidden helper text linking the two date inputs together for SR */}
        <span id="childcare-date-help" className="sr-only">
          {t('parentOnboarding.childcare.sessions.filters.fromToHelp')}
        </span>

        {/* Reset */}
        <button
          type="button"
          onClick={resetFilters}
          data-testid="childcare-reset-filters"
          className="px-3 py-1.5 text-xs rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream"
        >
          {t('parentOnboarding.childcare.sessions.filters.resetButton')}
        </button>

        {/* "New session" - library_admin only. Backend re-enforces. */}
        {isLibraryAdmin && (
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            data-testid="childcare-new-session"
            className="ml-auto inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            {t('parentOnboarding.childcare.sessions.create.button')}
          </button>
        )}
      </div>

      {/* Sessions Grid */}
      {sessions.length === 0 ? (
        <div className="text-center py-12">
          <Baby className="w-12 h-12 text-lsc-dark/20 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/60">
            {hasActiveFilters
              ? t('parentOnboarding.childcare.sessions.empty.matchingFilters')
              : t('parentOnboarding.childcare.sessions.empty.noSessionsAtAll')}
          </p>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={resetFilters}
              data-testid="childcare-empty-reset"
              className="mt-3 px-3 py-1.5 text-xs rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream"
            >
              {t('parentOnboarding.childcare.sessions.filters.resetButton')}
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sessions.map((session: ChildcareSession) => {
            const spotsLeft = session.max_children - session.registered_count
            const isFull = session.status === 'full' || spotsLeft <= 0
            const branchName = branchNameById.get(session.branch_id)
            return (
              <div
                key={session.id}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 flex flex-col"
              >
                <div className="flex items-start justify-between mb-3">
                  <h2 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    {sessionLabel(session)}
                  </h2>
                  <SessionStatusBadge status={session.status} />
                </div>

                <div className="space-y-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex-1">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-3.5 h-3.5 text-lsc-dark/70 dark:text-lsc-cream/50" />
                    {formatDate(session.date, language)}
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-lsc-dark/70 dark:text-lsc-cream/50" />
                    {session.start_time} - {session.end_time}
                  </div>
                  {branchName && (
                    <div className="flex items-center gap-2">
                      <MapPin className="w-3.5 h-3.5 text-lsc-dark/70 dark:text-lsc-cream/50" />
                      {branchName}
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <Users className="w-3.5 h-3.5 text-lsc-dark/70 dark:text-lsc-cream/50" />
                    {session.registered_count}/{session.max_children} {t('registered')}
                    {!isFull && (
                      <span className="text-status-success-600 dark:text-status-success-400 font-medium">
                        ({spotsLeft} {t('spots left')})
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Baby className="w-3.5 h-3.5 text-lsc-dark/70 dark:text-lsc-cream/50" />
                    {t('parentOnboarding.childcare.sessions.card.rangeLabel', {
                      min: session.age_range_min_months,
                      max: session.age_range_max_months,
                    })}
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-lsc-border dark:border-earth-700">
                  {session.status === 'available' && !isFull ? (
                    <button
                      onClick={() => openRegister(session.id)}
                      className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
                    >
                      <CheckCircle className="w-4 h-4" />
                      {t('Register')}
                    </button>
                  ) : (
                    <p className="text-center text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                      {isFull ? t('Session Full') : t('Registration not available')}
                    </p>
                  )}

                  {showStaffRoster && (
                    <div className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700">
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedRosterSessionId((prev) =>
                            prev === session.id ? null : session.id,
                          )
                        }
                        aria-expanded={expandedRosterSessionId === session.id}
                        className="w-full text-left text-xs font-medium"
                      >
                        {expandedRosterSessionId === session.id ? 'Hide roster' : 'View roster (staff)'}
                      </button>
                      {expandedRosterSessionId === session.id && (
                        <div className="mt-2">
                          <StaffRosterPanel
                            sessionId={session.id}
                            pickupFlagOn={pickupFlagOn}
                            onCheckout={(reg) => setCheckoutTarget(reg)}
                            onMarkNoShow={(reg) => setNoShowTarget(reg)}
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {checkoutTarget && (
        <StaffChildcareCheckoutModal
          registration={checkoutTarget}
          open={!!checkoutTarget}
          onClose={() => setCheckoutTarget(null)}
        />
      )}

      {noShowTarget && (
        <NoShowModal
          registration={noShowTarget}
          onClose={() => setNoShowTarget(null)}
        />
      )}

      {/* Registration Modal */}
      {showRegisterModal && (
        <ModalBackdrop onClose={resetForm} labelledBy={ids.modalTitle}>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 id={ids.modalTitle} className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                {selectedSession
                  ? `${t('Register for Childcare')}: ${sessionLabel(selectedSession)}`
                  : t('Register for Childcare')}
              </h2>
              <button onClick={resetForm} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg" aria-label={t('aria.authModals.close')}>
                <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" aria-hidden="true" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Child Name */}
              <div>
                <label
                  htmlFor={ids.childName}
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
                >
                  {t('Child Name')}{' '}
                  <span className="text-status-danger-500">
                    <span className="sr-only">{requiredSrLabel}</span>*
                  </span>
                </label>
                <input
                  id={ids.childName}
                  type="text"
                  required
                  aria-required="true"
                  aria-invalid={Boolean(fieldErrors.childName)}
                  aria-describedby={fieldErrors.childName ? `${ids.childName}-err` : undefined}
                  value={childName}
                  onChange={(e) => setChildName(e.target.value)}
                  className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
                {fieldErrors.childName && (
                  <p
                    id={`${ids.childName}-err`}
                    role="alert"
                    className="text-xs text-status-danger-700 dark:text-status-danger-300 mt-1"
                  >
                    {fieldErrors.childName}
                  </p>
                )}
              </div>

              {/* Child Age (years; converted to months at POST time) */}
              <div>
                <label
                  htmlFor={ids.childAgeYears}
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
                >
                  {t('Child Age (in years)')}{' '}
                  <span className="text-status-danger-500">
                    <span className="sr-only">{requiredSrLabel}</span>*
                  </span>
                </label>
                <input
                  id={ids.childAgeYears}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  required
                  aria-required="true"
                  aria-invalid={Boolean(fieldErrors.childAgeYears)}
                  aria-describedby={fieldErrors.childAgeYears ? `${ids.childAgeYears}-err` : undefined}
                  value={childAgeYears}
                  onChange={(e) => setChildAgeYears(e.target.value)}
                  className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
                {fieldErrors.childAgeYears && (
                  <p
                    id={`${ids.childAgeYears}-err`}
                    role="alert"
                    className="text-xs text-status-danger-700 dark:text-status-danger-300 mt-1"
                  >
                    {fieldErrors.childAgeYears}
                  </p>
                )}
              </div>

              {/* Emergency Contact Name */}
              <div>
                <label
                  htmlFor={ids.emergencyContactName}
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
                >
                  {t('Emergency Contact Name')}{' '}
                  <span className="text-status-danger-500">
                    <span className="sr-only">{requiredSrLabel}</span>*
                  </span>
                </label>
                <input
                  id={ids.emergencyContactName}
                  type="text"
                  required
                  aria-required="true"
                  aria-invalid={Boolean(fieldErrors.emergencyContactName)}
                  aria-describedby={
                    fieldErrors.emergencyContactName ? `${ids.emergencyContactName}-err` : undefined
                  }
                  value={emergencyContactName}
                  onChange={(e) => setEmergencyContactName(e.target.value)}
                  className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
                {fieldErrors.emergencyContactName && (
                  <p
                    id={`${ids.emergencyContactName}-err`}
                    role="alert"
                    className="text-xs text-status-danger-700 dark:text-status-danger-300 mt-1"
                  >
                    {fieldErrors.emergencyContactName}
                  </p>
                )}
              </div>

              {/* Emergency Contact Phone */}
              <div>
                <label
                  htmlFor={ids.emergencyContactPhone}
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
                >
                  {t('Emergency Contact Phone')}{' '}
                  <span className="text-status-danger-500">
                    <span className="sr-only">{requiredSrLabel}</span>*
                  </span>
                </label>
                <input
                  id={ids.emergencyContactPhone}
                  type="tel"
                  required
                  aria-required="true"
                  aria-invalid={Boolean(fieldErrors.emergencyContactPhone)}
                  aria-describedby={
                    fieldErrors.emergencyContactPhone ? `${ids.emergencyContactPhone}-err` : undefined
                  }
                  value={emergencyContactPhone}
                  onChange={(e) => setEmergencyContactPhone(e.target.value)}
                  className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
                {fieldErrors.emergencyContactPhone && (
                  <p
                    id={`${ids.emergencyContactPhone}-err`}
                    role="alert"
                    className="text-xs text-status-danger-700 dark:text-status-danger-300 mt-1"
                  >
                    {fieldErrors.emergencyContactPhone}
                  </p>
                )}
              </div>

              {/* Allergies (optional) */}
              <div>
                <label
                  htmlFor={ids.allergies}
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
                >
                  {t('Allergies')}
                </label>
                <input
                  id={ids.allergies}
                  type="text"
                  value={allergies}
                  onChange={(e) => setAllergies(e.target.value)}
                  className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  placeholder={t('List any allergies')}
                />
              </div>

              {/* Special Needs (optional) */}
              <div>
                <label
                  htmlFor={ids.specialNeeds}
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
                >
                  {t('Special Needs')}
                </label>
                <textarea
                  id={ids.specialNeeds}
                  value={specialNeeds}
                  onChange={(e) => setSpecialNeeds(e.target.value)}
                  rows={2}
                  className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  placeholder={t('Any special needs or accommodations')}
                />
              </div>
            </div>

            <div className="flex items-center gap-2 justify-end mt-6">
              <button
                onClick={resetForm}
                className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
              >
                {t('Cancel')}
              </button>
              <button
                onClick={handleRegister}
                disabled={registerMutation.isPending}
                className="flex items-center gap-1.5 px-4 py-2 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
              >
                {registerMutation.isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                {t('Register')}
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}

      {/* Create-session modal (library_admin only) */}
      {showCreateModal && (
        <ModalBackdrop
          onClose={() => setShowCreateModal(false)}
          labelledBy="childcare-create-modal-title"
        >
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2
                id="childcare-create-modal-title"
                className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
              >
                {t('parentOnboarding.childcare.sessions.create.heading')}
              </h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
                aria-label={t('aria.authModals.close')}
              >
                <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" aria-hidden="true" />
              </button>
            </div>

            <div className="space-y-3">
              {/* Branch */}
              <div>
                <label htmlFor="childcare-create-branch" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  {t('parentOnboarding.childcare.sessions.create.branchLabel')}
                </label>
                <select
                  id="childcare-create-branch"
                  value={createBranchId}
                  onChange={(e) => setCreateBranchId(e.target.value)}
                  required
                  aria-required="true"
                  className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="">--</option>
                  {branches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.short_name || b.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date */}
              <div>
                <label htmlFor="childcare-create-date" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  {t('parentOnboarding.childcare.sessions.create.dateLabel')}
                </label>
                <input
                  id="childcare-create-date"
                  type="date"
                  required
                  aria-required="true"
                  min={todayLocalISO()}
                  value={createDate}
                  onChange={(e) => setCreateDate(e.target.value)}
                  className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>

              {/* Start + End time row */}
              <div className="flex gap-3">
                <div className="flex-1">
                  <label htmlFor="childcare-create-start" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {t('parentOnboarding.childcare.sessions.create.startLabel')}
                  </label>
                  <input
                    id="childcare-create-start"
                    type="time"
                    step={900}
                    required
                    aria-required="true"
                    value={createStartTime}
                    onChange={(e) => setCreateStartTime(e.target.value)}
                    className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div className="flex-1">
                  <label htmlFor="childcare-create-end" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {t('parentOnboarding.childcare.sessions.create.endLabel')}
                  </label>
                  <input
                    id="childcare-create-end"
                    type="time"
                    step={900}
                    required
                    aria-required="true"
                    value={createEndTime}
                    onChange={(e) => setCreateEndTime(e.target.value)}
                    className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </div>

              {/* Max children */}
              <div>
                <label htmlFor="childcare-create-max" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  {t('parentOnboarding.childcare.sessions.create.maxChildrenLabel')}
                </label>
                <input
                  id="childcare-create-max"
                  type="number"
                  min={1}
                  max={20}
                  required
                  aria-required="true"
                  value={createMaxChildren}
                  onChange={(e) => setCreateMaxChildren(e.target.value)}
                  className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>

              {/* Age min + Age max row */}
              <div className="flex gap-3">
                <div className="flex-1">
                  <label htmlFor="childcare-create-age-min" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {t('parentOnboarding.childcare.sessions.create.ageMinLabel')}
                  </label>
                  <input
                    id="childcare-create-age-min"
                    type="number"
                    min={0}
                    aria-describedby="childcare-create-age-min-help"
                    value={createAgeMin}
                    onChange={(e) => setCreateAgeMin(e.target.value)}
                    className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                  <p id="childcare-create-age-min-help" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                    {t('parentOnboarding.childcare.sessions.create.ageMinHelp')}
                  </p>
                </div>
                <div className="flex-1">
                  <label htmlFor="childcare-create-age-max" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {t('parentOnboarding.childcare.sessions.create.ageMaxLabel')}
                  </label>
                  <input
                    id="childcare-create-age-max"
                    type="number"
                    min={0}
                    aria-describedby="childcare-create-age-max-help"
                    value={createAgeMax}
                    onChange={(e) => setCreateAgeMax(e.target.value)}
                    className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                  <p id="childcare-create-age-max-help" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                    {t('parentOnboarding.childcare.sessions.create.ageMaxHelp')}
                  </p>
                </div>
              </div>

              {/* Optional: room + staff IDs. v1 keeps these as raw int
                  inputs; richer pickers (room from rooms API, staff from
                  a child_supervision_certified subset) are deferred to a
                  follow-up. See spec Open Questions. */}
              <div className="flex gap-3">
                <div className="flex-1">
                  <label htmlFor="childcare-create-room" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {t('parentOnboarding.childcare.sessions.create.roomLabel')}
                  </label>
                  <input
                    id="childcare-create-room"
                    type="number"
                    min={1}
                    value={createRoomId}
                    onChange={(e) => setCreateRoomId(e.target.value)}
                    className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div className="flex-1">
                  <label htmlFor="childcare-create-staff" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {t('parentOnboarding.childcare.sessions.create.staffLabel')}
                  </label>
                  <input
                    id="childcare-create-staff"
                    type="number"
                    min={1}
                    value={createStaffId}
                    onChange={(e) => setCreateStaffId(e.target.value)}
                    className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </div>

              {createError && (
                <p
                  role="alert"
                  aria-live="polite"
                  data-testid="childcare-create-error"
                  className="text-xs text-status-danger-700 dark:text-status-danger-300"
                >
                  {createError}
                </p>
              )}
            </div>

            <div className="flex items-center gap-2 justify-end mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
              >
                {t('parentOnboarding.childcare.sessions.create.cancelButton')}
              </button>
              <button
                onClick={handleCreateSubmit}
                disabled={createMutation.isPending}
                aria-busy={createMutation.isPending}
                data-testid="childcare-create-submit"
                className="flex items-center gap-1.5 px-4 py-2 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
              >
                {createMutation.isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                {t('parentOnboarding.childcare.sessions.create.submitButton')}
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </div>
    </AdminShell>
  )
}
