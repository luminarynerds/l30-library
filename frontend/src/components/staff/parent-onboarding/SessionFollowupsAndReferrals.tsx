/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Session follow-ups + referrals section for the parent-onboarding
 * session detail page. Self-contained: owns its own queries, mutations,
 * and forms so it can be dropped into the page without coupling to the
 * page's existing (drift-prone) session model.
 *
 * A11y:
 *   - Two distinct <section aria-labelledby="..."> regions
 *   - Each follow-up + referral row is a <li> inside a <ul aria-label=...>
 *   - Status text is rendered as words (open / done / overdue),
 *     not just by color
 *   - Required fields use aria-required + a visible asterisk
 *   - "Mark done" is a <button> with an explicit accessible name
 *
 * i18n keys live under parentOnboarding.followups.* and
 * parentOnboarding.referrals.* -- see en.json.
 */
import { useState, useEffect, useId, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Check, Loader2, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

import { useTranslation } from '@/i18n'
import {
  listSessionFollowups,
  createSessionFollowup,
  completeFollowup,
  deleteFollowup,
  listSessionReferrals,
  createSessionReferral,
  deleteReferral,
  searchPartnerAgencies,
  type SessionFollowup,
  type SessionReferral,
  type FollowupPriority,
  type PartnerAgency,
} from '@/api/domains/services/parent-onboarding-followups-api'

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-900'

function StatusBadge({ status, label }: { status: string; label: string }) {
  // Color hint is supplemental; the label text is the source of truth (a11y).
  const palette: Record<string, string> = {
    open: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-200',
    in_progress:
      'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-200',
    completed:
      'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-200',
    cancelled:
      'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
    made: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-200',
    scheduled:
      'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-200',
    declined_by_patron:
      'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
    declined_by_agency:
      'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
  }
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        palette[status] ?? 'bg-earth-100 text-earth-800 dark:bg-earth-800'
      }`}
    >
      {label}
    </span>
  )
}

// ============================================================================
// Follow-ups
// ============================================================================

interface FollowupsPanelProps {
  sessionId: number
}

function FollowupsPanel({ sessionId }: FollowupsPanelProps) {
  const { t } = useTranslation()
  const headingId = useId()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)

  const followupsQuery = useQuery({
    queryKey: ['parent-onboarding-followups', sessionId],
    queryFn: () => listSessionFollowups(sessionId),
    enabled: !isNaN(sessionId),
  })

  const completeMutation = useMutation({
    mutationFn: (vars: { id: number; completion_note?: string }) =>
      completeFollowup(vars.id, { completion_note: vars.completion_note }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['parent-onboarding-followups', sessionId],
      })
      toast.success(t('parentOnboarding.followups.toast.completed'))
    },
    onError: () => {
      toast.error(t('parentOnboarding.followups.toast.completeError'))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteFollowup(id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['parent-onboarding-followups', sessionId],
      })
      toast.success(t('parentOnboarding.followups.toast.deleted'))
    },
    onError: () => {
      toast.error(t('parentOnboarding.followups.toast.deleteError'))
    },
  })

  return (
    <section
      aria-labelledby={headingId}
      className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5"
    >
      <div className="flex items-center justify-between mb-3">
        <h2
          id={headingId}
          className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
        >
          {t('parentOnboarding.followups.heading')}
        </h2>
        {!showForm && (
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-status-info-600 text-white rounded-lg hover:bg-status-info-700 transition-colors ${FOCUS_RING}`}
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            {t('parentOnboarding.followups.add')}
          </button>
        )}
      </div>

      {showForm && (
        <FollowupForm
          sessionId={sessionId}
          onCancel={() => setShowForm(false)}
          onCreated={() => {
            setShowForm(false)
            queryClient.invalidateQueries({
              queryKey: ['parent-onboarding-followups', sessionId],
            })
          }}
        />
      )}

      {followupsQuery.isLoading ? (
        <div
          className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 py-4"
          aria-live="polite"
        >
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
          {t('parentOnboarding.followups.loading')}
        </div>
      ) : followupsQuery.isError ? (
        <div
          role="alert"
          className="flex items-center gap-2 text-sm text-status-danger-700 py-4"
        >
          <AlertCircle className="w-4 h-4" aria-hidden="true" />
          {t('parentOnboarding.followups.loadError')}
        </div>
      ) : (followupsQuery.data?.followups.length ?? 0) === 0 ? (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 py-2">
          {t('parentOnboarding.followups.empty')}
        </p>
      ) : (
        <ul
          aria-label={t('parentOnboarding.followups.heading')}
          className="space-y-3"
        >
          {followupsQuery.data!.followups.map((f) => (
            <FollowupRow
              key={f.id}
              followup={f}
              onComplete={(note) =>
                completeMutation.mutate({ id: f.id, completion_note: note })
              }
              onDelete={() => deleteMutation.mutate(f.id)}
            />
          ))}
        </ul>
      )}
    </section>
  )
}

function FollowupRow({
  followup,
  onComplete,
  onDelete,
}: {
  followup: SessionFollowup
  onComplete: (note?: string) => void
  onDelete: () => void
}) {
  const { t } = useTranslation()
  const [completing, setCompleting] = useState(false)
  const [note, setNote] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const labelId = useId()

  useEffect(() => {
    if (completing) textareaRef.current?.focus()
  }, [completing])

  const statusLabel = t(
    `parentOnboarding.followups.status.${followup.status}` as const,
  )
  const isDone =
    followup.status === 'completed' || followup.status === 'cancelled'

  return (
    <li
      aria-labelledby={labelId}
      className="border border-lsc-border dark:border-earth-700 rounded-lg p-3"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <StatusBadge status={followup.status} label={statusLabel} />
            <span id={labelId} className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {followup.title}
            </span>
          </div>
          <div className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('parentOnboarding.followups.due')}: {followup.due_date}
            {followup.assignee_name
              ? ` · ${t('parentOnboarding.followups.assignee')}: ${followup.assignee_name}`
              : ''}
          </div>
          {followup.description && (
            <p className="mt-2 text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">
              {followup.description}
            </p>
          )}
          {followup.completion_note && (
            <p className="mt-2 text-sm italic text-lsc-dark/80 dark:text-lsc-cream/80">
              &ldquo;{followup.completion_note}&rdquo;
            </p>
          )}
        </div>
        {!isDone && !completing && (
          <button
            type="button"
            onClick={() => setCompleting(true)}
            className={`inline-flex items-center gap-1 px-3 py-1.5 text-xs bg-status-success-600 text-white rounded ${FOCUS_RING}`}
          >
            <Check className="w-3 h-3" aria-hidden="true" />
            {t('parentOnboarding.followups.markDone')}
          </button>
        )}
      </div>
      {completing && (
        <div className="mt-3 space-y-2">
          <label
            htmlFor={`completion-note-${followup.id}`}
            className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
          >
            {t('parentOnboarding.followups.completionNote')}
          </label>
          <textarea
            id={`completion-note-${followup.id}`}
            ref={textareaRef}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            placeholder={t('parentOnboarding.followups.markDoneHint')}
          />
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                onComplete(note.trim() || undefined)
                setCompleting(false)
              }}
              className={`px-3 py-1 text-xs bg-status-success-600 text-white rounded ${FOCUS_RING}`}
            >
              {t('parentOnboarding.followups.confirm')}
            </button>
            <button
              type="button"
              onClick={() => {
                setCompleting(false)
                setNote('')
              }}
              className={`px-3 py-1 text-xs border border-lsc-border dark:border-earth-600 rounded ${FOCUS_RING}`}
            >
              {t('parentOnboarding.followups.cancel')}
            </button>
          </div>
        </div>
      )}
      <div className="mt-2 text-right">
        <button
          type="button"
          onClick={onDelete}
          className={`text-xs text-status-danger-600 hover:underline ${FOCUS_RING}`}
          aria-label={t('parentOnboarding.followups.deleteAria', { title: followup.title })}
        >
          {t('parentOnboarding.followups.delete')}
        </button>
      </div>
    </li>
  )
}

function FollowupForm({
  sessionId,
  onCancel,
  onCreated,
}: {
  sessionId: number
  onCancel: () => void
  onCreated: () => void
}) {
  const { t } = useTranslation()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [priority, setPriority] = useState<FollowupPriority>('normal')
  const titleId = useId()
  const descId = useId()
  const dueId = useId()
  const prioId = useId()

  const createMutation = useMutation({
    mutationFn: () =>
      createSessionFollowup(sessionId, {
        title: title.trim(),
        description: description.trim() || undefined,
        due_date: dueDate,
        priority,
      }),
    onSuccess: () => {
      toast.success(t('parentOnboarding.followups.toast.created'))
      onCreated()
    },
    onError: () => {
      toast.error(t('parentOnboarding.followups.toast.createError'))
    },
  })

  const canSubmit = title.trim().length > 0 && dueDate.length > 0

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (canSubmit) createMutation.mutate()
      }}
      className="mb-4 space-y-3 border border-lsc-border dark:border-earth-700 rounded-lg p-3 bg-lsc-cream/30 dark:bg-earth-700/30"
    >
      <div>
        <label
          htmlFor={titleId}
          className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
        >
          {t('parentOnboarding.followups.title')}{' '}
          <span aria-hidden="true">*</span>
          <span className="sr-only">{t('parentOnboarding.required')}</span>
        </label>
        <input
          id={titleId}
          type="text"
          required
          aria-required="true"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        />
      </div>
      <div>
        <label
          htmlFor={descId}
          className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
        >
          {t('parentOnboarding.followups.description')}
        </label>
        <textarea
          id={descId}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label
            htmlFor={dueId}
            className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
          >
            {t('parentOnboarding.followups.due')}{' '}
            <span aria-hidden="true">*</span>
            <span className="sr-only">{t('parentOnboarding.required')}</span>
          </label>
          <input
            id={dueId}
            type="date"
            required
            aria-required="true"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          />
        </div>
        <div>
          <label
            htmlFor={prioId}
            className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
          >
            {t('parentOnboarding.followups.priority')}
          </label>
          <select
            id={prioId}
            value={priority}
            onChange={(e) => setPriority(e.target.value as FollowupPriority)}
            className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="low">{t('parentOnboarding.followups.priorityLevel.low')}</option>
            <option value="normal">{t('parentOnboarding.followups.priorityLevel.normal')}</option>
            <option value="high">{t('parentOnboarding.followups.priorityLevel.high')}</option>
          </select>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={!canSubmit || createMutation.isPending}
          className={`inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-status-info-600 text-white rounded disabled:opacity-50 ${FOCUS_RING}`}
        >
          {createMutation.isPending && (
            <Loader2 className="w-3 h-3 animate-spin" aria-hidden="true" />
          )}
          {t('parentOnboarding.followups.save')}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className={`px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-600 rounded ${FOCUS_RING}`}
        >
          {t('parentOnboarding.followups.cancel')}
        </button>
      </div>
    </form>
  )
}

// ============================================================================
// Referrals
// ============================================================================

interface ReferralsPanelProps {
  sessionId: number
}

function ReferralsPanel({ sessionId }: ReferralsPanelProps) {
  const { t } = useTranslation()
  const headingId = useId()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)

  const referralsQuery = useQuery({
    queryKey: ['parent-onboarding-referrals', sessionId],
    queryFn: () => listSessionReferrals(sessionId),
    enabled: !isNaN(sessionId),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteReferral(id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['parent-onboarding-referrals', sessionId],
      })
      toast.success(t('parentOnboarding.referrals.toast.deleted'))
    },
    onError: () => {
      toast.error(t('parentOnboarding.referrals.toast.deleteError'))
    },
  })

  return (
    <section
      aria-labelledby={headingId}
      className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5"
    >
      <div className="flex items-center justify-between mb-3">
        <h2
          id={headingId}
          className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
        >
          {t('parentOnboarding.referrals.heading')}
        </h2>
        {!showForm && (
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-status-info-600 text-white rounded-lg hover:bg-status-info-700 transition-colors ${FOCUS_RING}`}
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            {t('parentOnboarding.referrals.add')}
          </button>
        )}
      </div>

      {showForm && (
        <ReferralForm
          sessionId={sessionId}
          onCancel={() => setShowForm(false)}
          onCreated={() => {
            setShowForm(false)
            queryClient.invalidateQueries({
              queryKey: ['parent-onboarding-referrals', sessionId],
            })
          }}
        />
      )}

      {referralsQuery.isLoading ? (
        <div
          className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 py-4"
          aria-live="polite"
        >
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
          {t('parentOnboarding.referrals.loading')}
        </div>
      ) : referralsQuery.isError ? (
        <div
          role="alert"
          className="flex items-center gap-2 text-sm text-status-danger-700 py-4"
        >
          <AlertCircle className="w-4 h-4" aria-hidden="true" />
          {t('parentOnboarding.referrals.loadError')}
        </div>
      ) : (referralsQuery.data?.referrals.length ?? 0) === 0 ? (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 py-2">
          {t('parentOnboarding.referrals.empty')}
        </p>
      ) : (
        <ul
          aria-label={t('parentOnboarding.referrals.heading')}
          className="space-y-3"
        >
          {referralsQuery.data!.referrals.map((r) => (
            <ReferralRow
              key={r.id}
              referral={r}
              onDelete={() => deleteMutation.mutate(r.id)}
            />
          ))}
        </ul>
      )}
    </section>
  )
}

function ReferralRow({
  referral,
  onDelete,
}: {
  referral: SessionReferral
  onDelete: () => void
}) {
  const { t } = useTranslation()
  const agencyName =
    referral.partner_agency_name ||
    referral.agency_name_freetext ||
    t('parentOnboarding.referrals.agencyUnknown')
  const statusLabel = t(
    `parentOnboarding.referrals.status.${referral.status}` as const,
  )
  return (
    <li className="border border-lsc-border dark:border-earth-700 rounded-lg p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <StatusBadge status={referral.status} label={statusLabel} />
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {agencyName}
            </span>
          </div>
          <div className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('parentOnboarding.referrals.purpose')}: {referral.purpose}
          </div>
          {referral.warm_handoff && (
            <span className="inline-block mt-1 text-xs text-status-success-700 dark:text-status-success-200">
              {t('parentOnboarding.referrals.warmHandoff')}
            </span>
          )}
          {referral.notes && (
            <p className="mt-2 text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">
              {referral.notes}
            </p>
          )}
        </div>
      </div>
      <div className="mt-2 text-right">
        <button
          type="button"
          onClick={onDelete}
          className={`text-xs text-status-danger-600 hover:underline ${FOCUS_RING}`}
          aria-label={t('parentOnboarding.referrals.deleteAria', { agency: agencyName })}
        >
          {t('parentOnboarding.referrals.delete')}
        </button>
      </div>
    </li>
  )
}

function ReferralForm({
  sessionId,
  onCancel,
  onCreated,
}: {
  sessionId: number
  onCancel: () => void
  onCreated: () => void
}) {
  const { t } = useTranslation()
  const [agencyQuery, setAgencyQuery] = useState('')
  const [selectedAgency, setSelectedAgency] = useState<PartnerAgency | null>(
    null,
  )
  const [freetextOnly, setFreetextOnly] = useState(false)
  const [purpose, setPurpose] = useState('')
  const [notes, setNotes] = useState('')
  const [warmHandoff, setWarmHandoff] = useState(false)
  const [consent, setConsent] = useState(false)
  const agencyId = useId()
  const purposeId = useId()
  const notesId = useId()

  // Live autocomplete -- enabled only when the user typed something and no
  // agency is selected. The "create as free text" toggle bypasses lookup
  // entirely so an agency name not on file can still be captured.
  const agencyQueryResult = useQuery({
    queryKey: ['parent-onboarding-agencies', agencyQuery],
    queryFn: () => searchPartnerAgencies(agencyQuery, 8),
    enabled: !freetextOnly && agencyQuery.trim().length >= 2 && !selectedAgency,
  })

  const createMutation = useMutation({
    mutationFn: () =>
      createSessionReferral(sessionId, {
        partner_agency_id: selectedAgency?.id,
        agency_name_freetext:
          !selectedAgency && agencyQuery.trim()
            ? agencyQuery.trim()
            : undefined,
        purpose: purpose.trim(),
        warm_handoff: warmHandoff,
        patron_consent_to_share: consent,
        notes: notes.trim() || undefined,
      }),
    onSuccess: () => {
      toast.success(t('parentOnboarding.referrals.toast.created'))
      onCreated()
    },
    onError: () => {
      toast.error(t('parentOnboarding.referrals.toast.createError'))
    },
  })

  const canSubmit =
    purpose.trim().length > 0 &&
    ((selectedAgency != null) ||
      (freetextOnly && agencyQuery.trim().length > 0) ||
      (!freetextOnly && agencyQuery.trim().length > 0))

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (canSubmit) createMutation.mutate()
      }}
      className="mb-4 space-y-3 border border-lsc-border dark:border-earth-700 rounded-lg p-3 bg-lsc-cream/30 dark:bg-earth-700/30"
    >
      <div>
        <label
          htmlFor={agencyId}
          className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
        >
          {freetextOnly
            ? t('parentOnboarding.referrals.agencyFreetext')
            : t('parentOnboarding.referrals.agency')}{' '}
          <span aria-hidden="true">*</span>
          <span className="sr-only">{t('parentOnboarding.required')}</span>
        </label>
        <input
          id={agencyId}
          type="text"
          required
          aria-required="true"
          value={selectedAgency ? selectedAgency.name : agencyQuery}
          onChange={(e) => {
            setAgencyQuery(e.target.value)
            setSelectedAgency(null)
          }}
          className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        />
        {!freetextOnly &&
          !selectedAgency &&
          (agencyQueryResult.data?.agencies.length ?? 0) > 0 && (
            <ul
              role="listbox"
              aria-label={t('parentOnboarding.referrals.agencyListboxLabel')}
              className="mt-1 border border-lsc-border dark:border-earth-600 rounded bg-lsc-white dark:bg-earth-700 max-h-40 overflow-auto"
            >
              {agencyQueryResult.data!.agencies.map((a) => (
                <li key={a.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={false}
                    onClick={() => {
                      setSelectedAgency(a)
                      setAgencyQuery(a.name)
                    }}
                    className={`block w-full text-left px-2 py-1 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-600 ${FOCUS_RING}`}
                  >
                    {a.name}
                    {a.agency_type && (
                      <span className="ml-2 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                        ({a.agency_type})
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        <label className="mt-1 inline-flex items-center gap-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          <input
            type="checkbox"
            checked={freetextOnly}
            onChange={(e) => {
              setFreetextOnly(e.target.checked)
              setSelectedAgency(null)
            }}
          />
          {t('parentOnboarding.referrals.freetextToggle')}
        </label>
      </div>
      <div>
        <label
          htmlFor={purposeId}
          className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
        >
          {t('parentOnboarding.referrals.purpose')}{' '}
          <span aria-hidden="true">*</span>
          <span className="sr-only">{t('parentOnboarding.required')}</span>
        </label>
        <input
          id={purposeId}
          type="text"
          required
          aria-required="true"
          value={purpose}
          onChange={(e) => setPurpose(e.target.value)}
          className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        />
      </div>
      <div>
        <label
          htmlFor={notesId}
          className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
        >
          {t('parentOnboarding.referrals.notes')}
        </label>
        <textarea
          id={notesId}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded px-2 py-1 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        />
      </div>
      <div className="flex flex-wrap gap-4">
        <label className="inline-flex items-center gap-1.5 text-sm text-lsc-dark dark:text-lsc-cream">
          <input
            type="checkbox"
            checked={warmHandoff}
            onChange={(e) => setWarmHandoff(e.target.checked)}
          />
          {t('parentOnboarding.referrals.warmHandoff')}
        </label>
        <label className="inline-flex items-center gap-1.5 text-sm text-lsc-dark dark:text-lsc-cream">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />
          {t('parentOnboarding.referrals.patronConsent')}
        </label>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={!canSubmit || createMutation.isPending}
          className={`inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-status-info-600 text-white rounded disabled:opacity-50 ${FOCUS_RING}`}
        >
          {createMutation.isPending && (
            <Loader2 className="w-3 h-3 animate-spin" aria-hidden="true" />
          )}
          {t('parentOnboarding.referrals.save')}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className={`px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-600 rounded ${FOCUS_RING}`}
        >
          {t('parentOnboarding.referrals.cancel')}
        </button>
      </div>
    </form>
  )
}

// ============================================================================
// Section wrapper
// ============================================================================

interface Props {
  sessionId: number
}

export function SessionFollowupsAndReferrals({ sessionId }: Props) {
  if (isNaN(sessionId)) return null
  return (
    <div className="space-y-6">
      <FollowupsPanel sessionId={sessionId} />
      <ReferralsPanel sessionId={sessionId} />
    </div>
  )
}

export default SessionFollowupsAndReferrals
