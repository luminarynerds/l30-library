/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SeriesRegistrationModal — register a patron for every upcoming occurrence
 * in a recurring series in one step.
 *
 * Deliberately separate from RegistrationModal: series registration has no
 * per-occurrence waitlist branch, no photo-release step, and a different
 * success view. Sharing one modal would mean conditional logic threaded
 * through a critical single-event registration path.
 */
import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Loader2, CheckCircle, CalendarCheck, Clock } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { useAuth } from '@/contexts/AuthContext'
import {
  registerForSeries,
  type RegistrationCreate,
  type SeriesRegistrationOutcome,
  type SeriesRegistrationResult,
} from '@/api/events-api'
import type { Event } from '@/services/api'
import { useTranslation } from '@/i18n'
import { useEventPersonalization } from '@/hooks/useEventPersonalization'
import { TurnstileWidget } from '@/components/TurnstileWidget'

interface SeriesRegistrationModalProps {
  seriesId: string
  seriesName: string
  /** Upcoming occurrences in the series — used for the count and for
   *  per-occurrence personalization lookups (location/title). */
  seriesEvents: Event[]
  onClose: () => void
}

function outcomeBadge(
  status: SeriesRegistrationOutcome['status'],
  t: (key: string, fallback: string) => string,
): { label: string; classes: string } {
  switch (status) {
    case 'registered':
      return {
        label: t('seriesRegistration.outcome.registered', 'Registered'),
        classes:
          'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300',
      }
    case 'already_registered':
      return {
        label: t('seriesRegistration.outcome.alreadyRegistered', 'Already registered'),
        classes: 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark/80 dark:text-lsc-cream/80',
      }
    case 'waitlisted':
      return {
        label: t('seriesRegistration.outcome.waitlisted', 'Waitlisted'),
        classes:
          'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300',
      }
    case 'capacity_full':
      return {
        label: t('seriesRegistration.outcome.full', 'Full'),
        classes:
          'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300',
      }
    default:
      return {
        label: t('seriesRegistration.outcome.skipped', 'No registration needed'),
        classes: 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70',
      }
  }
}

export default function SeriesRegistrationModal({
  seriesId,
  seriesName,
  seriesEvents,
  onClose,
}: SeriesRegistrationModalProps): React.ReactElement {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { t, language } = useTranslation()
  const personalization = useEventPersonalization()
  const previousActiveElement = useRef<HTMLElement | null>(null)
  const successHeadingRef = useRef<HTMLHeadingElement | null>(null)

  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
      previousActiveElement.current?.focus()
    }
  }, [])

  const [formData, setFormData] = useState<RegistrationCreate>({
    patron_name: user?.first_name && user?.last_name ? `${user.first_name} ${user.last_name}` : '',
    patron_email: user?.email || '',
    patron_phone: user?.phone || '',
    // Opt-IN, matching RegistrationModal: reminders are off unless checked.
    reminder_requested: false,
  })
  const [success, setSuccess] = useState(false)
  const [result, setResult] = useState<SeriesRegistrationResult | null>(null)
  const [turnstileToken, setTurnstileToken] = useState('')

  const mutation = useMutation({
    mutationFn: (data: RegistrationCreate) => registerForSeries(seriesId, data),
    onSuccess: (data: SeriesRegistrationResult) => {
      personalization.setUserEmail(formData.patron_email ?? null)
      // Mirror each confirmed/waitlisted occurrence into client-side
      // personalization so MyEventsSection reflects the series immediately.
      for (const outcome of data.outcomes) {
        if (
          outcome.registration_id != null &&
          (outcome.status === 'registered' || outcome.status === 'waitlisted')
        ) {
          const occurrence = seriesEvents.find((e) => e.id === outcome.event_id)
          personalization.addRegistration({
            registrationId: outcome.registration_id,
            eventId: outcome.event_id,
            eventTitle: seriesName,
            eventStartTime: outcome.start_time,
            eventLocation: occurrence?.location ?? null,
            registeredAt: new Date().toISOString(),
            status: outcome.status === 'registered' ? 'confirmed' : outcome.status,
            reminderRequested: formData.reminder_requested ?? false,
          })
        }
      }
      setResult(data)
      setSuccess(true)
      queryClient.invalidateQueries({ queryKey: ['events'] })
      queryClient.invalidateQueries({ queryKey: ['my-registrations'] })
    },
  })

  useEffect(() => {
    if (success) {
      successHeadingRef.current?.focus()
    }
  }, [success])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate({ ...formData, turnstile_token: turnstileToken || 'unverified' })
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const sessionCount = seriesEvents.length

  return (
    <FocusTrap
      focusTrapOptions={{
        escapeDeactivates: false,
        allowOutsideClick: true,
        returnFocusOnDeactivate: false,
        fallbackFocus: () => document.body,
      }}
    >
      <div
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        role="presentation"
        onKeyDown={(e) => {
          if (e.key === 'Escape') onClose()
        }}
      >
        <div
          className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full max-h-[90vh] overflow-y-auto"
          role="dialog"
          aria-modal="true"
          aria-labelledby="series-registration-modal-title"
        >
          <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
            <h2
              id="series-registration-modal-title"
              className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
            >
              {success
                ? t('seriesRegistration.title.confirmed', 'Series Registration Confirmed')
                : t('seriesRegistration.title.register', 'Register for the Series')}
            </h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors"
              aria-label={t('aria.authModals.close', 'Close')}
            >
              <X aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            </button>
          </div>

          <div className="p-4">
            {success && result ? (
              <div>
                <div className="text-center py-2">
                  <CheckCircle
                    aria-hidden="true"
                    className="w-14 h-14 text-lsc-rose mx-auto mb-3"
                  />
                  <h3
                    ref={successHeadingRef}
                    tabIndex={-1}
                    className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1 focus:outline-none"
                  >
                    {t('seriesRegistration.success.heading', "You're signed up")}
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                    {t('seriesRegistration.success.summary', {
                      registered: result.registered_count + result.already_registered_count,
                      total: result.total_upcoming,
                      series: seriesName,
                    })}
                  </p>
                </div>
                <ul className="space-y-1.5 mb-4">
                  {result.outcomes.map((outcome) => {
                    const badge = outcomeBadge(outcome.status, t)
                    return (
                      <li
                        key={outcome.event_id}
                        className="flex items-center justify-between gap-2 text-sm"
                      >
                        <span className="flex items-center gap-1.5 text-lsc-dark/80 dark:text-lsc-cream/80 min-w-0">
                          <Clock aria-hidden="true" className="w-3.5 h-3.5 flex-shrink-0" />
                          <span className="truncate">
                            {new Intl.DateTimeFormat(language, {
                              weekday: 'short',
                              month: 'short',
                              day: 'numeric',
                            }).format(new Date(outcome.start_time))}
                          </span>
                        </span>
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${badge.classes}`}
                        >
                          {badge.label}
                          {outcome.status === 'waitlisted' && outcome.waitlist_position != null
                            ? ` #${outcome.waitlist_position}`
                            : ''}
                        </span>
                      </li>
                    )
                  })}
                </ul>
                <button
                  onClick={onClose}
                  className="w-full px-6 py-2 bg-lsc-rose hover:bg-lsc-rose-dark text-white rounded-xl transition-colors"
                >
                  {t('common.done', 'Done')}
                </button>
              </div>
            ) : (
              <>
                <div className="mb-4 p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl">
                  <h3 className="flex items-center gap-2 font-medium text-lsc-dark dark:text-lsc-cream">
                    <CalendarCheck aria-hidden="true" className="w-4 h-4 text-lsc-rose" />
                    {seriesName}
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                    {t('seriesRegistration.sessionCount', { count: sessionCount })}
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label
                      htmlFor="series_patron_name"
                      className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
                    >
                      {t('registration.field.fullName', 'Full Name *')}
                    </label>
                    <input
                      type="text"
                      id="series_patron_name"
                      name="patron_name"
                      required
                      value={formData.patron_name}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="series_patron_email"
                      className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
                    >
                      {t('registration.field.email', 'Email Address *')}
                    </label>
                    <input
                      type="email"
                      id="series_patron_email"
                      name="patron_email"
                      required
                      value={formData.patron_email}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="series_patron_phone"
                      className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
                    >
                      {t('registration.field.phone', 'Phone Number (optional)')}
                    </label>
                    <input
                      type="tel"
                      id="series_patron_phone"
                      name="patron_phone"
                      value={formData.patron_phone}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    />
                  </div>

                  <div className="flex items-start gap-2 pt-1">
                    <input
                      type="checkbox"
                      id="series_reminder_requested"
                      name="reminder_requested"
                      checked={formData.reminder_requested ?? false}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          reminder_requested: e.target.checked,
                        }))
                      }
                      className="mt-1 h-4 w-4 rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
                    />
                    <label
                      htmlFor="series_reminder_requested"
                      className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80"
                    >
                      {t(
                        'registration.field.reminderRequested',
                        'Send me a reminder 24 hours before this event',
                      )}
                    </label>
                  </div>

                  {mutation.isError && (
                    <div
                      role="alert"
                      aria-live="assertive"
                      className="p-3 bg-status-danger-50 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 rounded-xl text-sm"
                    >
                      {mutation.error.message}
                    </div>
                  )}

                  <div className="pt-2">
                    <TurnstileWidget onVerify={setTurnstileToken} />
                  </div>

                  <div className="flex gap-3 pt-2">
                    <button
                      type="button"
                      onClick={onClose}
                      className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"
                    >
                      {t('common.cancel', 'Cancel')}
                    </button>
                    <button
                      type="submit"
                      disabled={mutation.isPending || !turnstileToken}
                      className="flex-1 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose-dark disabled:opacity-60 text-white rounded-xl transition-colors flex items-center justify-center gap-2"
                    >
                      {mutation.isPending ? (
                        <>
                          <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                          {t('registration.button.registering', 'Registering...')}
                        </>
                      ) : (
                        t('seriesRegistration.button.registerAll', 'Register for all sessions')
                      )}
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    </FocusTrap>
  )
}
