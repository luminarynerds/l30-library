/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Verification trail components for ParentResourcesPage.
 *
 * Three pieces live in this file so the parent page stays focused on
 * layout + handout mode:
 *
 *   - <VerifiedBadge>: the "Verified Mar 2026 by Rosa T." line under each
 *     item. Reads the verification fields off the item and picks an
 *     appropriate string (verified / never-verified / stale).
 *
 *   - <FlagOutOfDateModal>: the radio-group dialog opened by the
 *     "Flag as out of date" button. Submits to POST /flags and emits
 *     onSubmitted on success so the page can toast + invalidate cache.
 *
 *   - useStaffPredicate(): tiny hook resolving "should we show the Verify
 *     still current button" off the AuthContext. Staff and above only.
 *     The page itself is staff-routed today but the spec is explicit that
 *     a future patron-facing version of the page would NOT show this
 *     button -- so we keep the predicate honest.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, Loader2, ShieldCheck } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useTranslation } from '@/i18n'
import {
  flagResourceGuideItem,
  type ResourceGuideFlagReason,
  type ResourceGuideItem,
} from '@/api/parent-onboarding-api'
import * as Sentry from '@/lib/sentry-lazy'

/**
 * Roles that may verify / view the staff queue. Spec: staff and above.
 * Defensive set: staff, library_admin, admin, super_admin, director.
 */
const STAFF_ROLES = new Set(['staff', 'library_admin', 'admin', 'super_admin', 'director'])

export function useStaffPredicate(): boolean {
  const { user } = useAuth()
  return !!user && STAFF_ROLES.has(user.role ?? '')
}

function formatVerifiedMonth(isoTimestamp: string, locale: string): string {
  try {
    const d = new Date(isoTimestamp)
    return new Intl.DateTimeFormat(locale, {
      month: 'short',
      year: 'numeric',
    }).format(d)
  } catch (err) {
    Sentry.addBreadcrumb({
      category: 'i18n',
      level: 'warning',
      message: 'VerifiedBadge: Intl.DateTimeFormat threw, falling back',
      data: { iso: isoTimestamp, err: String(err) },
    })
    return isoTimestamp.slice(0, 7) // YYYY-MM
  }
}

interface VerifiedBadgeProps {
  item: ResourceGuideItem
  /** Months threshold; from backend setting parent_resource_stale_after_months. */
  staleAfterMonths: number
  /** Show "Verify still current" CTA (staff-only). */
  showVerifyButton: boolean
  /** Called when the verify button is clicked; busy state owned by parent. */
  onVerify?: () => void
  /** Called when "Flag as out of date" is clicked. */
  onFlag: () => void
  /** True while a verify request is in flight; disables the button. */
  verifyBusy?: boolean
}

export function VerifiedBadge({
  item,
  staleAfterMonths,
  showVerifyButton,
  onVerify,
  onFlag,
  verifyBusy = false,
}: VerifiedBadgeProps): JSX.Element {
  const translation = useTranslation()
  const t = translation.t
  // Older tests in this repo mock useTranslation() to a `{ t }` shape with
  // no `i18n` property; guard so consumers without locale awareness still
  // render. The badge falls back to 'en' formatting which is fine for
  // assertions of structure.
  const i18n = (translation as { i18n?: { language?: string } }).i18n
  const locale = i18n?.language ?? 'en'

  const isStale = item.stale ?? item.last_verified_at == null
  const neverVerified = item.last_verified_at == null
  const verifiedMonth = item.last_verified_at
    ? formatVerifiedMonth(item.last_verified_at, locale)
    : null
  const verifierName = item.verified_by_name?.trim() || null

  let line: string
  if (neverVerified) {
    line = t('parentResources.verified.never')
  } else if (verifierName) {
    line = t('parentResources.verified.by', {
      date: verifiedMonth,
      name: verifierName,
    })
  } else {
    line = t('parentResources.verified.byUnknown', { date: verifiedMonth })
  }

  const staleSuffix = isStale && !neverVerified
    ? ` ${t('parentResources.verified.stale', { months: staleAfterMonths })}`
    : ''

  const openFlagCount = item.open_flag_count ?? 0

  return (
    <div
      data-testid={`verified-badge-${item.id}`}
      data-stale={isStale ? 'true' : 'false'}
      className="flex flex-wrap items-center gap-3 mt-3 text-xs text-lsc-dark/60 dark:text-lsc-cream/70"
    >
      <span className="inline-flex items-center gap-1.5">
        {isStale ? (
          <AlertTriangle
            className="w-3.5 h-3.5 text-status-warning-500"
            aria-hidden="true"
          />
        ) : (
          <ShieldCheck
            className="w-3.5 h-3.5 text-status-success-500"
            aria-hidden="true"
          />
        )}
        <span>
          {line}
          {staleSuffix}
        </span>
      </span>

      {showVerifyButton && onVerify && (
        <button
          type="button"
          onClick={onVerify}
          disabled={verifyBusy}
          aria-label={t('parentResources.actions.verifyCurrentAria', { title: item.title })}
          data-testid={`verify-item-${item.id}`}
          className="inline-flex items-center gap-1 text-lsc-rose hover:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1 rounded disabled:opacity-50 print:hidden"
        >
          {verifyBusy && <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" aria-hidden="true" />}
          {t('parentResources.actions.verifyCurrent')}
        </button>
      )}

      <button
        type="button"
        onClick={onFlag}
        aria-label={t('parentResources.actions.flagOutOfDateAria', { title: item.title })}
        data-testid={`flag-item-${item.id}`}
        className="inline-flex items-center gap-1 text-lsc-rose hover:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1 rounded print:hidden"
      >
        {t('parentResources.actions.flagOutOfDate')}
      </button>

      {openFlagCount > 0 && (
        <span
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-status-warning-50 text-status-warning-700 text-[10px] font-medium uppercase tracking-wide"
          data-testid={`flag-pill-${item.id}`}
        >
          {t('parentResources.flagged.pill', { count: openFlagCount })}
        </span>
      )}
    </div>
  )
}

const REASON_CODES: ResourceGuideFlagReason[] = [
  'disconnected_phone',
  'wrong_address',
  'eligibility_changed',
  'closed_permanently',
  'other',
]

interface FlagOutOfDateModalProps {
  item: ResourceGuideItem
  onClose: () => void
  onSubmitted: () => void
}

export function FlagOutOfDateModal({
  item,
  onClose,
  onSubmitted,
}: FlagOutOfDateModalProps): JSX.Element {
  const { t } = useTranslation()
  const [reason, setReason] = useState<ResourceGuideFlagReason>('disconnected_phone')
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const firstInputRef = useRef<HTMLInputElement | null>(null)

  // Escape-to-close; initial focus to first radio.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    firstInputRef.current?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await flagResourceGuideItem(item.id, {
        reason_code: reason,
        comment: comment.trim() || undefined,
      })
      onSubmitted()
    } catch (err) {
      Sentry.captureException(err)
      setError(t('parentResources.flagModal.submitError'))
    } finally {
      setSubmitting(false)
    }
  }

  const titleId = `flag-modal-title-${item.id}`

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 print:hidden"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
      onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-6"
        data-testid="flag-modal"
      >
        <h2
          id={titleId}
          className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4"
        >
          {t('parentResources.flagModal.title', { title: item.title })}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              {t('parentResources.flagModal.legend')}
            </legend>
            {REASON_CODES.map((code, idx) => (
              <label
                key={code}
                className="flex items-start gap-2 text-sm text-lsc-dark dark:text-lsc-cream cursor-pointer"
              >
                <input
                  ref={idx === 0 ? firstInputRef : undefined}
                  type="radio"
                  name={`flag-reason-${item.id}`}
                  value={code}
                  checked={reason === code}
                  onChange={() => setReason(code)}
                  className="mt-0.5 w-4 h-4 text-lsc-rose focus:ring-2 focus:ring-lsc-rose"
                  data-testid={`flag-reason-${code}`}
                />
                <span>
                  {t(`parentResources.flagModal.reason.${code}`)}
                </span>
              </label>
            ))}
          </fieldset>

          <label className="block">
            <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              {t('parentResources.flagModal.commentLabel')}
            </span>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value.slice(0, 500))}
              rows={3}
              maxLength={500}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              data-testid="flag-comment"
            />
          </label>

          {error && (
            <p
              role="alert"
              className="text-sm text-status-danger-600 dark:text-status-danger-300"
            >
              {error}
            </p>
          )}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              {t('parentResources.flagModal.cancel')}
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
              data-testid="flag-submit"
            >
              {submitting && (
                <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" aria-hidden="true" />
              )}
              {t('parentResources.flagModal.submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function useIsStale(item: ResourceGuideItem): boolean {
  return useMemo(() => {
    if (item.stale !== undefined) return item.stale
    return item.last_verified_at == null
  }, [item.stale, item.last_verified_at])
}
