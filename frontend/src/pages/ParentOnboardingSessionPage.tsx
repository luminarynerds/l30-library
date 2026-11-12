/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as Sentry from "@/lib/sentry-lazy"
import {
  Loader2,
  Calendar,
  MapPin,
  User,
  Save,
  CheckCircle,
  ArrowLeft,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getSession,
  updateSession,
  completeSession,
  type ParentOnboardingSessionDetail,
  type ParentOnboardingStatus,
} from '@/api/parent-onboarding-api'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { parseDate } from '@/utils/format-utils'
import { SessionFollowupsAndReferrals } from '@/components/staff/parent-onboarding/SessionFollowupsAndReferrals'
import { SessionResourceHandouts } from '@/components/staff/parent-onboarding/SessionResourceHandouts'
import { FamilySnapshot } from '@/components/staff/parent-onboarding/FamilySnapshot'
import { usePiiAccessLog } from '@/hooks/usePiiAccessLog'

export function scrubPatronError(err: unknown): {
  message: string
  status?: number
  endpoint?: string
} {
  if (!err || typeof err !== 'object') {
    return { message: typeof err === 'string' ? err : 'Unknown error' }
  }
  const e = err as {
    message?: unknown
    status?: unknown
    response?: { status?: unknown; config?: { url?: unknown }; data?: unknown }
    config?: { url?: unknown }
  }
  const message = typeof e.message === 'string' ? e.message : 'Unknown error'
  const status =
    typeof e.status === 'number'
      ? e.status
      : typeof e.response?.status === 'number'
        ? e.response.status
        : undefined
  const endpoint =
    typeof e.response?.config?.url === 'string'
      ? e.response.config.url
      : typeof e.config?.url === 'string'
        ? e.config.url
        : undefined
  return { message, status, endpoint }
}

// Combines date + time from the single `scheduled_at` datetime column.
function formatScheduled(iso: string): string {
  const parsed = parseDate(iso)
  if (!parsed) return '-'
  const locale = getCurrentLocale()
  const datePart = parsed.toLocaleDateString(locale, { month: 'short', day: 'numeric', year: 'numeric' })
  const timePart = parsed.toLocaleTimeString(locale, { hour: 'numeric', minute: '2-digit' })
  return `${datePart}, ${timePart}`
}

function StatusBadge({ status }: { status: string }) {
  const base = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium'
  const colors: Record<string, string> = {
    scheduled: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    in_progress: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-400',
    completed: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
    cancelled: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    no_show: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
  }
  return (
    <span className={`${base} ${colors[status] ?? 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300'}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

export default function ParentOnboardingSessionPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const sessionId = Number(id)
  const logPiiAccess = usePiiAccessLog()

  const [isEditing, setIsEditing] = useState(false)
  const [editNotes, setEditNotes] = useState('')
  const [editStatus, setEditStatus] = useState<ParentOnboardingStatus>('scheduled')

  // Complete session form
  const [showCompleteForm, setShowCompleteForm] = useState(false)
  const [completionNotes, setCompletionNotes] = useState('')

  const {
    data: session,
    isLoading,
    error,
  } = useQuery<ParentOnboardingSessionDetail>({
    queryKey: ['parent-onboarding-session', sessionId],
    queryFn: async () => {
      const data = await getSession(sessionId)
      // Real granular PII audit log write -- see usePiiAccessLog hook.
      // Fire-and-forget; errors are absorbed inside the hook.
      logPiiAccess({
        patronId: data.patron_id,
        subjectType: 'parent_onboarding_session',
        subjectId: sessionId,
        action: 'read',
      })
      return data
    },
    enabled: !isNaN(sessionId),
  })

  const updateMutation = useMutation({
    mutationFn: (data: {
      family_situation_notes?: string
      status?: ParentOnboardingStatus
    }) => updateSession(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['parent-onboarding-session', sessionId] })
      toast.success(t('parentOnboarding.sessionPage.toast.updateSuccess'))
      setIsEditing(false)
    },
    onError: (err) => {
      Sentry.captureException(scrubPatronError(err), { tags: { sessionId: String(sessionId) } })
      toast.error(t('parentOnboarding.sessionPage.toast.updateError'))
    },
  })

  const completeMutation = useMutation({
    mutationFn: (data: { family_situation_notes?: string }) => completeSession(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['parent-onboarding-session', sessionId] })
      queryClient.invalidateQueries({ queryKey: ['parent-onboarding-dashboard'] })
      toast.success(t('parentOnboarding.sessionPage.toast.completeSuccess'))
      setShowCompleteForm(false)
    },
    onError: (err) => {
      Sentry.captureException(scrubPatronError(err), { tags: { sessionId: String(sessionId) } })
      toast.error(t('parentOnboarding.sessionPage.toast.completeError'))
    },
  })

  function startEditing() {
    if (!session) return
    setEditNotes(session.family_situation_notes ?? '')
    setEditStatus(session.status)
    setIsEditing(true)
  }

  function handleSave() {
    updateMutation.mutate({
      family_situation_notes: editNotes,
      status: editStatus,
    })
  }

  function handleComplete() {
    completeMutation.mutate({
      ...(completionNotes && { family_situation_notes: completionNotes }),
    })
  }

  if (error) {
    Sentry.captureException(scrubPatronError(error), { tags: { sessionId: String(sessionId) } })
  }

  const pageTitle = t('parentOnboarding.sessionPage.pageTitle')
  const errorMessage = error || !session ? t('parentOnboarding.sessionPage.loadError') : null

  return (
    <AdminShell
      title={pageTitle}
      loading={isLoading}
      error={!isLoading ? errorMessage : null}
    >
      {session && (
        <div className="max-w-4xl mx-auto p-6 space-y-6">
          {/* Header */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(-1)}
              aria-label={t('parentOnboarding.sessionPage.back')}
              className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" />
            </button>
            <div className="flex-1">
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                {t('parentOnboarding.sessionPage.heading', { id: String(session.id) })}
              </h1>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('parentOnboarding.sessionPage.patronFallback', { id: String(session.patron_id) })}
              </p>
            </div>
            <StatusBadge status={session.status} />
          </div>

          {/* Session Details */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                {t('parentOnboarding.sessionPage.detailsHeading')}
              </h2>
              {session.status !== 'completed' && session.status !== 'cancelled' && (
                <div className="flex items-center gap-2">
                  {!isEditing && (
                    <button
                      onClick={startEditing}
                      className="px-3 py-1.5 text-sm bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-border dark:hover:bg-earth-600 transition-colors"
                    >
                      {t('parentOnboarding.sessionPage.edit')}
                    </button>
                  )}
                  {!showCompleteForm && !isEditing && (
                    <button
                      onClick={() => setShowCompleteForm(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 transition-colors"
                    >
                      <CheckCircle className="w-4 h-4" />
                      {t('parentOnboarding.sessions.complete')}
                    </button>
                  )}
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center gap-3">
                <User className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" aria-hidden="true" />
                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{t('parentOnboarding.sessionPage.fields.patron')}</p>
                  <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                    {`#${session.patron_id}`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <User className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" aria-hidden="true" />
                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{t('parentOnboarding.sessionPage.fields.staff')}</p>
                  <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                    {session.staff_id ? `#${session.staff_id}` : t('parentOnboarding.sessionPage.unassigned')}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Calendar className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" aria-hidden="true" />
                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{t('parentOnboarding.sessionPage.fields.date')}</p>
                  <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                    {formatScheduled(session.scheduled_at)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <MapPin className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" aria-hidden="true" />
                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{t('parentOnboarding.sessionPage.fields.branch')}</p>
                  <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                    {`#${session.branch_id}`}
                  </p>
                </div>
              </div>
            </div>

            {/* Notes */}
            <div className="mt-4">
              {isEditing ? (
                <>
                  <label
                    htmlFor="session-notes"
                    className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 block mb-1"
                  >
                    {t('parentOnboarding.sessionPage.fields.notes')}
                  </label>
                  <textarea
                    id="session-notes"
                    value={editNotes}
                    onChange={(e) => setEditNotes(e.target.value)}
                    rows={3}
                    className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </>
              ) : (
                <>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mb-1">{t('parentOnboarding.sessionPage.fields.notes')}</p>
                  <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                    {session.family_situation_notes ?? t('parentOnboarding.sessionPage.noNotes')}
                  </p>
                </>
              )}
            </div>

            {/* Edit actions */}
            {isEditing && (
              <div className="flex items-center gap-2 mt-4">
                <label htmlFor="session-status" className="sr-only">
                  {t('parentOnboarding.sessionPage.fields.status')}
                </label>
                <select
                  id="session-status"
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value as ParentOnboardingStatus)}
                  className="text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="scheduled">{t('parentOnboarding.sessions.status.scheduled')}</option>
                  <option value="in_progress">{t('parentOnboarding.sessions.status.in_progress')}</option>
                  <option value="cancelled">{t('parentOnboarding.sessions.status.cancelled')}</option>
                  <option value="no_show">{t('parentOnboarding.sessions.status.no_show')}</option>
                </select>
                <div className="flex-1" />
                <button
                  onClick={() => setIsEditing(false)}
                  className="px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                >
                  {t('parentOnboarding.sessionPage.cancel')}
                </button>
                <button
                  onClick={handleSave}
                  disabled={updateMutation.isPending}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
                >
                  {updateMutation.isPending ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" /> : <Save className="w-4 h-4" aria-hidden="true" />}
                  {t('parentOnboarding.sessionPage.save')}
                </button>
              </div>
            )}
          </div>

          {/* Complete Session Form */}
          {showCompleteForm && (
            <div className="bg-status-success-50 dark:bg-status-success-900/10 rounded-xl border border-status-success-200 dark:border-status-success-800/30 p-5">
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                {t('parentOnboarding.sessions.complete')}
              </h3>
              <div className="space-y-4">
                <div>
                  <label
                    htmlFor="session-complete-outcomes"
                    className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
                  >
                    {t('parentOnboarding.sessionPage.fields.outcomes')}
                  </label>
                  <textarea
                    id="session-complete-outcomes"
                    value={completionNotes}
                    onChange={(e) => setCompletionNotes(e.target.value)}
                    rows={3}
                    className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    placeholder={t('parentOnboarding.sessionPage.placeholders.outcomes')}
                  />
                </div>
                {/* Resource handouts and referrals are recorded via the
                    structured pickers below (SessionResourceHandouts,
                    SessionFollowupsAndReferrals) rather than freeform text
                    here -- see parent_onboarding.py model comments on
                    Components 8/9 for why those replaced this form. */}
                <div className="flex items-center gap-2 justify-end">
                  <button
                    onClick={() => setShowCompleteForm(false)}
                    className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                  >
                    {t('parentOnboarding.sessionPage.cancel')}
                  </button>
                  <button
                    onClick={handleComplete}
                    disabled={completeMutation.isPending}
                    className="flex items-center gap-1.5 px-4 py-2 text-sm bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 transition-colors disabled:opacity-50"
                  >
                    {completeMutation.isPending ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" /> : <CheckCircle className="w-4 h-4" aria-hidden="true" />}
                    {t('parentOnboarding.sessionPage.markComplete')}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Completed Session Info */}
          {session.status === 'completed' && session.family_situation_notes && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 space-y-3">
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                {t('parentOnboarding.sessionPage.outcomesHeading')}
              </h3>
              <div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mb-1">{t('parentOnboarding.sessionPage.fields.outcomes')}</p>
                <p className="text-sm text-lsc-dark dark:text-lsc-cream">{session.family_situation_notes}</p>
              </div>
            </div>
          )}

          {/* Family Snapshot pane (PR feat/session-family-snapshot, Phase F). */}
          <FamilySnapshot sessionId={sessionId} patronId={session.patron_id} />

          {/* First-class follow-ups + referrals (PR feat/session-followup-referrals). */}
          <SessionFollowupsAndReferrals sessionId={sessionId} />

          {/* Structured resource-handouts picker (PR feat/session-catalog-handout).
              `patronLanguage` is intentionally undefined here today: the family-
              snapshot spec will surface a real value, at which point the
              "Suggested for this family" group lights up. The picker still
              works without it -- it just doesn't auto-filter. */}
          <SessionResourceHandouts sessionId={sessionId} />
        </div>
      )}
    </AdminShell>
  )
}
