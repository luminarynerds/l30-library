/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Staff-mediated enrollment modal for a parent connection group.
 *
 * Inline patron autocomplete (uses searchPatronsSuggestions). PatronSearchBar
 * in components/staff/patrons/ is a styled <form>-with-input -- no result
 * list, no autocomplete affordance -- so we don't wrap it; we build the
 * input + result list here. Spec calls for "reuse"; the reusable primitive
 * is the underlying API helper, not the styled bar component.
 *
 * Admin gate (over-capacity override) is enforced both client-side (toggle
 * hidden for non-admin) and server-side (route returns 403).
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import * as Sentry from '@/lib/sentry-lazy'
import toast from 'react-hot-toast'
import { Loader2, AlertTriangle, Search } from 'lucide-react'

import { Modal } from '@/components/ui/Modal'
import { useAuth } from '@/contexts/AuthContext'
import { useTranslation } from '@/i18n'
import { searchPatronsSuggestions } from '@/api/staff-api/patrons'
import type { Patron } from '@/api/staff-api/patrons'
import {
  enrollPatronInGroup,
  requestToJoinConfidentialGroup,
  type EnrollMemberResponse,
  type ParentConnectionGroup,
} from '@/api/parent-onboarding-api'

const ADMIN_ROLES = new Set(['admin', 'super_admin', 'director'])

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-900'

const REDACTED_CTX = {
  tags: { group_type: '[redacted]' },
  extra: { group_id: '[redacted]' },
} as const

interface Props {
  group: ParentConnectionGroup
  isOpen: boolean
  onClose: () => void
}

export function EnrollPatronModal({ group, isOpen, onClose }: Props) {
  const { t } = useTranslation()
  const { token, user } = useAuth()
  const queryClient = useQueryClient()
  const isAdmin = !!(user?.role && ADMIN_ROLES.has(user.role))

  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Patron[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [selected, setSelected] = useState<Patron | null>(null)
  const [consentNote, setConsentNote] = useState('')
  const [overrideCapacity, setOverrideCapacity] = useState(false)
  const [justification, setJustification] = useState('')
  // Confidential-group inputs (only shown when group.confidential).
  const [requestMessage, setRequestMessage] = useState('')
  const [consentToShareContact, setConsentToShareContact] = useState(false)

  const isConfidential = group.confidential === true

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Reset modal state on open/close so the next session starts clean.
  useEffect(() => {
    if (!isOpen) {
      setQuery('')
      setResults([])
      setSelected(null)
      setConsentNote('')
      setOverrideCapacity(false)
      setJustification('')
      setRequestMessage('')
      setConsentToShareContact(false)
    }
  }, [isOpen])

  // Debounced search. searchPatronsSuggestions itself enforces the 2-char
  // minimum and an internal limit of 5 results -- spec calls for 8, but
  // bumping that requires a separate API change; flagged in PR body.
  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    if (!token || query.trim().length < 2) {
      setResults([])
      return
    }
    debounceTimer.current = setTimeout(async () => {
      setIsSearching(true)
      try {
        const r = await searchPatronsSuggestions(token, query.trim())
        setResults(r)
      } catch (err) {
        Sentry.captureException(err, REDACTED_CTX)
      } finally {
        setIsSearching(false)
      }
    }, 250)
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current)
    }
  }, [query, token])

  const capacity = useMemo(() => {
    const current = group.current_members ?? 0
    const max = group.max_members ?? 0
    const available = Math.max(0, max - current)
    return { current, max, available, isFull: available === 0 }
  }, [group])

  const mutation = useMutation({
    mutationFn: () => {
      if (!selected) throw new Error('no patron selected')
      if (isConfidential) {
        // Confidential groups: route through approval. Server enforces
        // facilitator/admin-auto-decide vs general-staff-pending branching
        // based on the caller's role; we always send the request shape.
        return requestToJoinConfidentialGroup(group.id, {
          patron_id: selected.id,
          request_message: requestMessage.trim() || undefined,
          consent_to_share_contact: consentToShareContact,
        })
      }
      return enrollPatronInGroup(group.id, {
        patron_id: selected.id,
        consent_note: consentNote.trim() || undefined,
        override_capacity: overrideCapacity,
        override_justification: overrideCapacity
          ? justification.trim() || undefined
          : undefined,
      })
    },
    onSuccess: (resp: EnrollMemberResponse | { status: string; estimated_response_window_hours?: number }) => {
      queryClient.invalidateQueries({ queryKey: ['connection-groups'] })
      const patronName = patronDisplayName(selected)
      if (isConfidential) {
        const hours =
          (resp as { estimated_response_window_hours?: number })
            .estimated_response_window_hours ?? 48
        if ((resp as { status: string }).status === 'pending_approval') {
          toast.success(
            t('connectionGroups.confidential.requestSent', { hours }),
          )
        } else {
          toast.success(
            t('parentOnboarding.connectionGroups.enroll.successActive', {
              patronName,
            }),
          )
        }
        onClose()
        return
      }
      const key =
        (resp as EnrollMemberResponse).status === 'waitlisted'
          ? 'parentOnboarding.connectionGroups.enroll.successWaitlist'
          : 'parentOnboarding.connectionGroups.enroll.successActive'
      toast.success(t(key, { patronName }))
      onClose()
    },
    onError: (err: unknown) => {
      Sentry.captureException(err, REDACTED_CTX)
      const detail =
        (err as { detail?: string; message?: string })?.detail ??
        (err as Error)?.message ??
        ''
      const patronName = patronDisplayName(selected)
      const msgKey = detail.toLowerCase().includes('already')
        ? 'parentOnboarding.connectionGroups.enroll.errorAlreadyMember'
        : 'parentOnboarding.connectionGroups.enroll.errorGeneric'
      toast.error(t(msgKey, { patronName }))
    },
  })

  const submitDisabled =
    !selected ||
    mutation.isPending ||
    (overrideCapacity && justification.trim().length < 10)

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (submitDisabled) return
    mutation.mutate()
  }

  const patronName = patronDisplayName(selected)

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('parentOnboarding.connectionGroups.enroll.title', {
        groupName: group.name,
      })}
      size="lg"
    >
      <form onSubmit={onSubmit} className="space-y-4">
        {/* Patron picker */}
        <div>
          <label
            htmlFor="enroll-patron-search"
            className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
          >
            {t('parentOnboarding.connectionGroups.enroll.patronLabel')}
          </label>
          <div className="relative">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/60 dark:text-lsc-cream/60"
              aria-hidden="true"
            />
            <input
              id="enroll-patron-search"
              type="text"
              value={query}
              onChange={e => {
                setQuery(e.target.value)
                setSelected(null)
              }}
              placeholder={t(
                'parentOnboarding.connectionGroups.enroll.patronPlaceholder',
              )}
              aria-autocomplete="list"
              aria-controls="enroll-patron-results"
              className={`w-full pl-9 pr-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream ${FOCUS_RING}`}
              data-testid="enroll-patron-input"
            />
          </div>

          {selected ? (
            <div
              className="mt-2 text-sm text-lsc-dark dark:text-lsc-cream"
              data-testid="enroll-patron-selected"
            >
              {patronName}
              {selected.library_card_number
                ? ` (${selected.library_card_number})`
                : ''}
            </div>
          ) : (
            <ul
              id="enroll-patron-results"
              role="listbox"
              aria-live="polite"
              className="mt-2 border border-lsc-border dark:border-earth-700 rounded-lg divide-y divide-lsc-border dark:divide-earth-700 max-h-48 overflow-y-auto"
              data-testid="enroll-patron-results"
            >
              {isSearching && (
                <li className="px-3 py-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-2">
                  <Loader2 className="w-3 h-3 motion-safe:animate-spin" aria-hidden="true" />
                  {t('parentOnboarding.connectionGroups.enroll.searching')}
                </li>
              )}
              {!isSearching && query.trim().length >= 2 && results.length === 0 && (
                <li className="px-3 py-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('parentOnboarding.connectionGroups.enroll.noResults')}
                </li>
              )}
              {results.map(p => (
                <li key={p.id} role="option" aria-selected="false">
                  <button
                    type="button"
                    onClick={() => {
                      setSelected(p)
                      setQuery(displayName(p))
                    }}
                    className={`w-full text-left px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 ${FOCUS_RING}`}
                    data-testid="enroll-patron-result"
                  >
                    {displayName(p)}
                    {p.library_card_number ? (
                      <span className="ml-2 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                        {p.library_card_number}
                      </span>
                    ) : null}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {isConfidential && (
          <div
            className="border border-lsc-border dark:border-earth-700 rounded-lg p-3 space-y-3"
            data-testid="enroll-confidential-section"
          >
            <p className="text-xs text-lsc-dark dark:text-lsc-cream">
              {group.confidential_approval_message ||
                t('connectionGroups.confidential.whatHappensNext', {
                  hours: group.estimated_response_window_hours ?? 48,
                })}
            </p>
            <div>
              <label
                htmlFor="enroll-request-message"
                className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
              >
                {t('connectionGroups.confidential.requestMessageLabel')}
              </label>
              <textarea
                id="enroll-request-message"
                value={requestMessage}
                onChange={e => setRequestMessage(e.target.value)}
                maxLength={500}
                rows={3}
                className={`w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream ${FOCUS_RING}`}
                data-testid="enroll-request-message"
              />
            </div>
            <label className="flex items-start gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
              <input
                type="checkbox"
                checked={consentToShareContact}
                onChange={e => setConsentToShareContact(e.target.checked)}
                aria-describedby="enroll-consent-share-hint"
                data-testid="enroll-consent-share-toggle"
                className="mt-1"
              />
              <span>
                {t('connectionGroups.confidential.consentLabel')}
                <span
                  id="enroll-consent-share-hint"
                  className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  {t('connectionGroups.confidential.consentHint')}
                </span>
              </span>
            </label>
          </div>
        )}

        {/* Capacity readout */}
        <div
          className="text-sm text-lsc-dark dark:text-lsc-cream flex items-start gap-2"
          data-testid="enroll-capacity-readout"
        >
          {capacity.isFull ? (
            <>
              <AlertTriangle
                className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400 mt-0.5"
                aria-hidden="true"
              />
              <span>
                {t(
                  'parentOnboarding.connectionGroups.enroll.capacityFull',
                  { current: capacity.current, max: capacity.max },
                )}
              </span>
            </>
          ) : (
            <span>
              {t(
                'parentOnboarding.connectionGroups.enroll.capacityAvailable',
                {
                  current: capacity.current,
                  max: capacity.max,
                  available: capacity.available,
                },
              )}
            </span>
          )}
        </div>

        {/* Consent note */}
        <div>
          <label
            htmlFor="enroll-consent-note"
            className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
          >
            {t('parentOnboarding.connectionGroups.enroll.consentLabel')}
          </label>
          <textarea
            id="enroll-consent-note"
            value={consentNote}
            onChange={e => setConsentNote(e.target.value)}
            maxLength={500}
            rows={3}
            aria-describedby="enroll-consent-hint"
            className={`w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream ${FOCUS_RING}`}
          />
          <p
            id="enroll-consent-hint"
            className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
          >
            {t('parentOnboarding.connectionGroups.enroll.consentHint')}
          </p>
        </div>

        {/* Override (admin only, full group only) */}
        {isAdmin && capacity.isFull && (
          <div
            className="border border-lsc-border dark:border-earth-700 rounded-lg p-3 space-y-2"
            data-testid="enroll-override-section"
          >
            <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
              <input
                type="checkbox"
                checked={overrideCapacity}
                onChange={e => setOverrideCapacity(e.target.checked)}
                aria-describedby="enroll-override-warning"
                data-testid="enroll-override-toggle"
              />
              {t('parentOnboarding.connectionGroups.enroll.overrideToggle')}
            </label>
            <p
              id="enroll-override-warning"
              className="text-xs text-status-warning-600 dark:text-status-warning-400 flex items-center gap-1"
            >
              <AlertTriangle className="w-3 h-3" aria-hidden="true" />
              {t('parentOnboarding.connectionGroups.enroll.overrideWarning')}
            </p>
            {overrideCapacity && (
              <div>
                <label
                  htmlFor="enroll-override-justification"
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
                >
                  {t(
                    'parentOnboarding.connectionGroups.enroll.justificationLabel',
                  )}
                </label>
                <textarea
                  id="enroll-override-justification"
                  value={justification}
                  onChange={e => setJustification(e.target.value)}
                  minLength={10}
                  maxLength={500}
                  rows={2}
                  required
                  className={`w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream ${FOCUS_RING}`}
                  data-testid="enroll-override-justification"
                />
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className={`px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 ${FOCUS_RING}`}
          >
            {t('parentOnboarding.connectionGroups.enroll.cancel')}
          </button>
          <button
            type="submit"
            disabled={submitDisabled}
            data-testid="enroll-submit"
            className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50 ${FOCUS_RING}`}
          >
            {mutation.isPending && (
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
            )}
            {selected
              ? t('parentOnboarding.connectionGroups.enroll.submit', {
                  patronName,
                })
              : t('parentOnboarding.connectionGroups.enroll.submitDisabled')}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function displayName(p: Patron): string {
  const full = `${p.first_name ?? ''} ${p.last_name ?? ''}`.trim()
  return full || p.email || `Patron #${p.id}`
}

function patronDisplayName(p: Patron | null): string {
  return p ? displayName(p) : ''
}

export default EnrollPatronModal
