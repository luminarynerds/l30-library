/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Family Snapshot pane for the parent-onboarding session detail page.
 *
 * Read-only mirror of patron + household + family-group data, gated by
 * the patron's ``family_snapshot`` consent. Sensitive fields (child
 * first names, full household notes) hide behind a Reveal button; both
 * the passive load and the Reveal click write a ``pii_access_log`` row
 * server-side. The Reveal state auto-collapses after 5 minutes of
 * inactivity.
 *
 * A11y:
 *   - <section aria-labelledby="family-snapshot-heading"> wrapper
 *   - <dl> rows with paired <dt>/<dd>
 *   - Reveal button is <button aria-pressed="true|false"> with text
 *     that swaps (Reveal / Hide), not just an icon
 *   - "Not on file" copy carries meaning, not just yellow color
 *   - prefers-reduced-motion honored on the fade-in
 *
 * EssentialsMode handling: the spec hides the snapshot entirely in
 * EssentialsMode (it's staff-facing; the calm-mode is patron-facing).
 * Page-level: check EssentialsMode before rendering this component.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2, Eye, EyeOff, Info, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

import { useTranslation } from '@/i18n'
import {
  getSessionFamilySnapshot,
  revealSessionFamilySnapshot,
  recordPatronFamilySnapshotConsent,
  type FamilySnapshot as FamilySnapshotData,
} from '@/api/parent-onboarding-api'

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-900'

// Reveal auto-collapses after this many milliseconds of inactivity. Per
// the Phase F brief: re-reveal requires a fresh click + a fresh audit
// row, so we err on the side of recollapsing rather than holding the
// staff session "unmasked" across context switches.
const REVEAL_IDLE_TIMEOUT_MS = 5 * 60 * 1000

interface FamilySnapshotProps {
  sessionId: number
  patronId: number
}

export function FamilySnapshot({ sessionId, patronId }: FamilySnapshotProps): JSX.Element {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  // ``revealed`` is the local view state; the server payload tells us
  // whether sensitive fields are actually present. When the user clicks
  // Reveal we swap in the reveal-endpoint payload.
  const [revealed, setRevealed] = useState(false)
  const [showConsentPrompt, setShowConsentPrompt] = useState(false)
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const snapshotQuery = useQuery<FamilySnapshotData>({
    queryKey: ['family-snapshot', sessionId],
    queryFn: () => getSessionFamilySnapshot(sessionId),
    enabled: Number.isFinite(sessionId) && sessionId > 0,
  })

  const revealMutation = useMutation({
    mutationFn: () => revealSessionFamilySnapshot(sessionId),
    onSuccess: (data) => {
      // Replace the cached redacted payload with the revealed one so
      // the rest of the surface re-renders without a second GET.
      queryClient.setQueryData(['family-snapshot', sessionId], data)
      setRevealed(true)
    },
    onError: () => {
      toast.error(t('parentOnboarding.familySnapshot.revealError'))
      setRevealed(false)
    },
  })

  const consentMutation = useMutation({
    mutationFn: (granted: boolean) =>
      recordPatronFamilySnapshotConsent(patronId, { granted }),
    onSuccess: (_data, granted) => {
      toast.success(
        granted
          ? t('parentOnboarding.familySnapshot.consentSaved')
          : t('parentOnboarding.familySnapshot.consentRevokedToast'),
      )
      setShowConsentPrompt(false)
      queryClient.invalidateQueries({ queryKey: ['family-snapshot', sessionId] })
      queryClient.invalidateQueries({
        queryKey: ['patron-family-snapshot-consent', patronId],
      })
    },
    onError: () => {
      toast.error(t('parentOnboarding.familySnapshot.consentSaveError'))
    },
  })

  // Idle-timer to auto-collapse the reveal state. Cleared on every
  // toggle so navigating back to the page while still revealed gives
  // the staff member a fresh 5-minute window.
  const clearIdleTimer = useCallback(() => {
    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current)
      idleTimerRef.current = null
    }
  }, [])

  const collapseReveal = useCallback(() => {
    clearIdleTimer()
    setRevealed(false)
    // Re-query the redacted payload so the next render shows initials.
    queryClient.invalidateQueries({ queryKey: ['family-snapshot', sessionId] })
  }, [clearIdleTimer, queryClient, sessionId])

  const armIdleTimer = useCallback(() => {
    clearIdleTimer()
    idleTimerRef.current = setTimeout(collapseReveal, REVEAL_IDLE_TIMEOUT_MS)
  }, [clearIdleTimer, collapseReveal])

  useEffect(() => {
    if (revealed) {
      armIdleTimer()
    } else {
      clearIdleTimer()
    }
    return clearIdleTimer
  }, [revealed, armIdleTimer, clearIdleTimer])

  const handleRevealClick = useCallback(() => {
    if (revealed) {
      collapseReveal()
    } else {
      revealMutation.mutate()
    }
  }, [revealed, collapseReveal, revealMutation])

  // Loading state.
  if (snapshotQuery.isLoading) {
    return (
      <section
        aria-labelledby="family-snapshot-heading"
        className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5"
      >
        <h2
          id="family-snapshot-heading"
          className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3"
        >
          {t('parentOnboarding.familySnapshot.heading')}
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-2">
          <Loader2
            className="w-4 h-4 motion-safe:animate-spin"
            aria-hidden="true"
          />
          {t('parentOnboarding.familySnapshot.loading')}
        </p>
      </section>
    )
  }

  // Error state.
  if (snapshotQuery.isError || !snapshotQuery.data) {
    return (
      <section
        aria-labelledby="family-snapshot-heading"
        className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5"
      >
        <h2
          id="family-snapshot-heading"
          className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3"
        >
          {t('parentOnboarding.familySnapshot.heading')}
        </h2>
        <p
          className="text-sm text-status-danger-700 dark:text-status-danger-300 flex items-center gap-2"
          role="alert"
        >
          <AlertCircle className="w-4 h-4" aria-hidden="true" />
          {t('parentOnboarding.familySnapshot.loadError')}
        </p>
      </section>
    )
  }

  const data = snapshotQuery.data
  const consentGranted = data.consent_status === 'granted'

  return (
    <section
      aria-labelledby="family-snapshot-heading"
      className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 motion-safe:transition-shadow"
    >
      <header className="flex items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-2 flex-wrap">
          <h2
            id="family-snapshot-heading"
            className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
          >
            {t('parentOnboarding.familySnapshot.heading')}
          </h2>
          <span
            className="text-lsc-dark/60 dark:text-lsc-cream/50"
            title={t('parentOnboarding.familySnapshot.sharedFromPatronTooltip')}
            aria-label={t('parentOnboarding.familySnapshot.sharedFromPatronTooltip')}
          >
            <Info className="w-4 h-4" aria-hidden="true" />
          </span>
        </div>
        {consentGranted ? (
          <button
            type="button"
            onClick={handleRevealClick}
            disabled={revealMutation.isPending}
            aria-pressed={revealed}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border transition-colors disabled:opacity-50 ${FOCUS_RING} ${
              revealed
                ? 'bg-lsc-rose text-white border-lsc-rose hover:bg-lsc-rose/90'
                : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-600 hover:bg-lsc-border dark:hover:bg-earth-600'
            }`}
          >
            {revealMutation.isPending ? (
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
            ) : revealed ? (
              <EyeOff className="w-4 h-4" aria-hidden="true" />
            ) : (
              <Eye className="w-4 h-4" aria-hidden="true" />
            )}
            {revealed
              ? t('parentOnboarding.familySnapshot.hide')
              : t('parentOnboarding.familySnapshot.reveal')}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setShowConsentPrompt((s) => !s)}
            aria-expanded={showConsentPrompt}
            aria-controls="family-snapshot-consent-prompt"
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 ${FOCUS_RING}`}
          >
            {t('parentOnboarding.familySnapshot.recordConsent')}
          </button>
        )}
      </header>

      <dl className="grid grid-cols-1 md:grid-cols-3 gap-x-4 gap-y-3 text-sm">
        <div>
          <dt className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
            {t('parentOnboarding.familySnapshot.languagePref')}
          </dt>
          <dd className="text-lsc-dark dark:text-lsc-cream">
            {data.language_preference_label
              ? `${data.language_preference_label}${
                  data.language_preference
                    ? ` (${data.language_preference})`
                    : ''
                }`
              : '—'}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
            {t('parentOnboarding.familySnapshot.householdSize')}
          </dt>
          <dd className="text-lsc-dark dark:text-lsc-cream">
            {consentGranted
              ? data.household_size != null
                ? data.household_size === 1
                  ? t('parentOnboarding.familySnapshot.householdSizeSinglePatron')
                  : t('parentOnboarding.familySnapshot.householdSizeValue', {
                      count: String(data.household_size),
                    })
                : '—'
              : t('parentOnboarding.familySnapshot.consentMissing')}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
            {t('parentOnboarding.familySnapshot.baby')}
          </dt>
          <dd className="text-lsc-dark dark:text-lsc-cream">
            {consentGranted
              ? data.baby_age_months != null
                ? t('parentOnboarding.familySnapshot.babyMonths', {
                    months: String(data.baby_age_months),
                  })
                : '—'
              : '—'}
          </dd>
        </div>
        <div className="md:col-span-3">
          <dt className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
            {t('parentOnboarding.familySnapshot.children')}
          </dt>
          <dd className="text-lsc-dark dark:text-lsc-cream">
            {!consentGranted ? (
              <span>{t('parentOnboarding.familySnapshot.consentMissing')}</span>
            ) : data.household_members.length === 0 ? (
              <span>{t('parentOnboarding.familySnapshot.empty')}</span>
            ) : (
              <ul
                aria-label={t('parentOnboarding.familySnapshot.children')}
                className="flex flex-wrap gap-1.5 mt-1"
              >
                {data.household_members.map((m, i) => (
                  <li
                    key={`${m.age_range}-${m.first_name_revealed}-${i}`}
                    className="inline-flex items-center px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-700 text-xs"
                  >
                    {m.age_range} ({m.first_name_revealed})
                  </li>
                ))}
              </ul>
            )}
          </dd>
        </div>
        <div className="md:col-span-3">
          <dt className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
            {t('parentOnboarding.familySnapshot.notes')}
          </dt>
          <dd className="text-lsc-dark dark:text-lsc-cream">
            {!consentGranted
              ? t('parentOnboarding.familySnapshot.consentMissing')
              : data.household_notes_summary ?? '—'}
          </dd>
        </div>
      </dl>

      {/* Consent prompt (inline form) */}
      {!consentGranted && showConsentPrompt && (
        <div
          id="family-snapshot-consent-prompt"
          className="mt-4 p-4 rounded-lg bg-lsc-cream/60 dark:bg-earth-700/40 border border-lsc-border dark:border-earth-600"
        >
          <p className="text-sm text-lsc-dark dark:text-lsc-cream mb-3">
            {t('parentOnboarding.familySnapshot.consentPrompt')}
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => consentMutation.mutate(true)}
              disabled={consentMutation.isPending}
              className={`px-3 py-1.5 text-sm bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 disabled:opacity-50 ${FOCUS_RING}`}
            >
              {consentMutation.isPending ? (
                <Loader2
                  className="w-4 h-4 motion-safe:animate-spin"
                  aria-hidden="true"
                />
              ) : (
                t('parentOnboarding.familySnapshot.recordConsent')
              )}
            </button>
            <button
              type="button"
              onClick={() => setShowConsentPrompt(false)}
              className={`px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream ${FOCUS_RING}`}
            >
              {t('parentOnboarding.sessionPage.cancel')}
            </button>
          </div>
        </div>
      )}

      <p className="mt-4 text-xs text-lsc-dark/60 dark:text-lsc-cream/50">
        {t('parentOnboarding.familySnapshot.auditHint')}
        {revealed && (
          <>
            {' '}
            {t('parentOnboarding.familySnapshot.autoCollapseHint')}
          </>
        )}
      </p>
    </section>
  )
}
