/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Loader2, CheckCircle } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { useAuth } from '@/contexts/AuthContext'
import { useBranding } from '@/contexts/BrandingContext'
import {
  registerForEvent,
  joinEventWaitlist,
  type Registration,
  type RegistrationCreate,
  type WaitlistJoinResult,
} from '@/api/events-api'
import type { Event } from '@/services/api'
import { useTranslation } from '@/i18n'
import { useEventPersonalization } from '@/hooks/useEventPersonalization'
import { TurnstileWidget } from '@/components/TurnstileWidget'

interface RegistrationModalProps {
  event: Event
  onClose: () => void
}

export default function RegistrationModal({ event, onClose }: RegistrationModalProps): React.ReactElement {
  const queryClient = useQueryClient()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user, token: _token } = useAuth()
  const { t, language } = useTranslation()
  const branding = useBranding()
  const personalization = useEventPersonalization()
  const previousActiveElement = useRef<HTMLElement | null>(null)
  const successHeadingRef = useRef<HTMLHeadingElement | null>(null)

  // Store trigger element and restore focus on close
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
    // Opt-IN: an emailed reminder is off unless the patron checks the box.
    // Pre-checked email consent is a dark pattern; the .ics export covers the
    // "help me remember" need without auto-enrolling anyone in email.
    reminder_requested: false,
    // Photo release consent. Defaults to null ("not yet answered" /
    // "not asked"). The submit handler decides whether to send the value
    // based on event.photos_will_be_taken.
    photo_release_granted: null,
  })
  const [success, setSuccess] = useState(false)
  const [contactError, setContactError] = useState<string | null>(null)
  const [registrationStatus, setRegistrationStatus] = useState<string>('')
  const [turnstileToken, setTurnstileToken] = useState('')
  // PR #999: waitlist UI state. When event is full we route the submit
  // through the new /waitlist endpoint and show position on success.
  const [waitlistResult, setWaitlistResult] = useState<WaitlistJoinResult | null>(null)
  const isFull = event.spots_remaining === 0

  const mutation = useMutation({
    mutationFn: (data: RegistrationCreate) => registerForEvent(event.id, data),
    onSuccess: (data: Registration) => {
      // Wire personalization BEFORE invalidating queries so anonymous patrons
      // see their registrations in MyEventsSection and can cancel via EventsPageContent.
      // Phone-only patrons skip the email-keyed personalization gracefully.
      if (formData.patron_email) personalization.setUserEmail(formData.patron_email)
      personalization.addRegistration({
        registrationId: data.id,
        eventId: data.event_id,
        eventTitle: event.title,
        eventStartTime: event.start_time,
        eventLocation: event.location,
        registeredAt: data.registered_at,
        status: data.status,
        reminderRequested: data.reminder_requested,
      })
      setRegistrationStatus(data.status)
      setSuccess(true)
      queryClient.invalidateQueries({ queryKey: ['events'] })
      queryClient.invalidateQueries({ queryKey: ['my-registrations'] })
    },
  })

  // PR #999: parallel mutation for full events.
  const waitlistMutation = useMutation({
    mutationFn: () =>
      joinEventWaitlist(event.id, {
        email: formData.patron_email ?? '',
        name: formData.patron_name || null,
        registrant_count: 1,
        notes: formData.accommodation_details || null,
        turnstile_token: turnstileToken || null,
      }),
    onSuccess: (data: WaitlistJoinResult) => {
      if (formData.patron_email) personalization.setUserEmail(formData.patron_email)
      setWaitlistResult(data)
      setRegistrationStatus('waitlisted')
      setSuccess(true)
      queryClient.invalidateQueries({ queryKey: ['events'] })
    },
  })


  // Move focus to success heading when the modal swaps to success view
  // so screen readers announce the state change.
  useEffect(() => {
    if (success) {
      successHeadingRef.current?.focus()
    }
  }, [success])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // One contact method is enough: email OR phone. The waitlist is the
    // exception — its invitation goes out by email.
    const hasEmail = Boolean(formData.patron_email?.trim())
    const hasPhone = Boolean(formData.patron_phone?.trim())
    if (!hasEmail && !hasPhone) {
      setContactError(
        t(
          'registration.error.contactRequired',
          'Please add an email or a phone number so we can reach you about this event.',
        ),
      )
      return
    }
    if (isFull && !hasEmail) {
      setContactError(
        t(
          'registration.error.waitlistNeedsEmail',
          'Waitlist invitations go out by email, so we need an email address for this one.',
        ),
      )
      return
    }
    setContactError(null)
    // Only include photo_release_granted when the event is asking.
    // If the event has photos_will_be_taken=false, send null so the server
    // can persist the three-valued "not asked" state.
    const base: RegistrationCreate = event.photos_will_be_taken
      ? formData
      : { ...formData, photo_release_granted: null }
    if (isFull) {
      waitlistMutation.mutate()
      return
    }
    mutation.mutate({ ...base, turnstile_token: turnstileToken || 'unverified' })
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev: RegistrationCreate) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }))
    if (e.target.name === 'patron_email' || e.target.name === 'patron_phone') {
      setContactError(null)
    }
  }

  const formattedEventDate = new Intl.DateTimeFormat(language, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(event.start_time))

  return (
    <FocusTrap focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: false, fallbackFocus: () => document.body }}>
      <div
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        role="presentation"
        onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
      >
      <div
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full"
        role="dialog"
        aria-modal="true"
        aria-labelledby="registration-modal-title"
      >
        <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
          <h2 id="registration-modal-title" className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {success
              ? t('registration.title.confirmed', 'Registration Confirmed')
              : t('registration.title.register', 'Register for Event')}
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors"
            aria-label={t('aria.authModals.close')}
          >
            <X aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </button>
        </div>

        <div className="p-4">
          {success ? (
            <div className="text-center py-6">
              <CheckCircle aria-hidden="true" className="w-16 h-16 text-lsc-rose dark:text-lsc-rose mx-auto mb-4" />
              <h3
                ref={successHeadingRef}
                tabIndex={-1}
                className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2 focus:outline-none"
              >
                {registrationStatus === 'waitlisted'
                  ? t('registration.success.heading.waitlisted', 'Added to Waitlist')
                  : t('registration.success.heading.registered', "You're Registered!")}
              </h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                {registrationStatus === 'waitlisted' && waitlistResult
                  ? t(
                      'waitlist.success.bodyWithPosition',
                      { position: waitlistResult.position, title: event.title }
                    )
                  : registrationStatus === 'waitlisted'
                  ? t('registration.success.body.waitlisted', { title: event.title })
                  : t('registration.success.body.registered', { title: event.title })}
              </p>
              <button
                onClick={onClose}
                className="px-6 py-2 bg-lsc-rose hover:bg-lsc-rose text-white rounded-xl transition-colors"
              >
                {t('common.done', 'Done')}
              </button>
            </div>
          ) : (
            <>
              <div className="mb-4 p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl">
                <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
                  {event.title}
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {formattedEventDate}
                </p>
                {event.spots_remaining !== null && (
                  <p className="text-sm text-lsc-rose dark:text-lsc-rose mt-1">
                    {event.spots_remaining > 0
                      ? t('registration.spotsRemaining', { count: event.spots_remaining })
                      : t('registration.eventFull', 'Event is full - join waitlist')}
                  </p>
                )}
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label
                    htmlFor="patron_name"
                    className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
                  >
                    {t('registration.field.fullName', 'Full Name *')}
                  </label>
                  <input
                    type="text"
                    id="patron_name"
                    name="patron_name"
                    required
                    value={formData.patron_name}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    placeholder={t('placeholder.registrationModal.johnSmith')}
                  />
                </div>

                <div>
                  <label
                    htmlFor="patron_email"
                    className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
                  >
                    {t('registration.field.email', 'Email Address')}
                  </label>
                  <input
                    type="email"
                    id="patron_email"
                    name="patron_email"
                    value={formData.patron_email ?? ''}
                    onChange={handleChange}
                    aria-describedby="contact_method_help"
                    aria-invalid={contactError ? true : undefined}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    placeholder={t('placeholder.registrationModal.johnexamplecom')}
                  />
                </div>

                <div>
                  <label
                    htmlFor="patron_phone"
                    className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1"
                  >
                    {t('registration.field.phone', 'Phone Number')}
                  </label>
                  <input
                    type="tel"
                    id="patron_phone"
                    name="patron_phone"
                    value={formData.patron_phone ?? ''}
                    onChange={handleChange}
                    aria-describedby="contact_method_help"
                    aria-invalid={contactError ? true : undefined}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    placeholder={t('placeholder.guestPassForm.5551234567')}
                  />
                </div>

                <div className="space-y-1">
                  <p
                    id="contact_method_help"
                    className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60"
                  >
                    {t(
                      'registration.help.contactMethod',
                      'Share an email or a phone number — whichever works for you. We just need one way to reach you.',
                    )}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                    {branding.phone
                      ? t('registration.help.noContactNote', {
                          phone: branding.phone,
                        })
                      : t(
                          'registration.help.noContactNoteGeneric',
                          "No email or phone? No problem — call the library or stop by the desk and we'll sign you up.",
                        )}
                  </p>
                  {contactError && (
                    <p
                      role="alert"
                      className="text-sm text-status-danger-700 dark:text-status-danger-300"
                    >
                      {contactError}
                    </p>
                  )}
                </div>

                <div className="flex items-start gap-2 pt-1">
                  <input
                    type="checkbox"
                    id="reminder_requested"
                    name="reminder_requested"
                    checked={formData.reminder_requested ?? false}
                    onChange={(e) =>
                      setFormData((prev: RegistrationCreate) => ({
                        ...prev,
                        reminder_requested: e.target.checked,
                      }))
                    }
                    className="mt-1 h-4 w-4 rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
                    aria-describedby="reminder_requested_help"
                  />
                  <div className="flex flex-col">
                    <label
                      htmlFor="reminder_requested"
                      className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80"
                    >
                      {t('registration.field.reminderRequested', 'Send me a reminder 24 hours before this event')}
                    </label>
                    <p
                      id="reminder_requested_help"
                      className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5"
                    >
                      {t(
                        'registration.help.reminderRequested',
                        "We'll send one email the day before. You can opt out anytime.",
                      )}
                    </p>
                  </div>
                </div>

                {event.photos_will_be_taken && (
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      id="photo_release_granted"
                      checked={formData.photo_release_granted === true}
                      onChange={(e) => setFormData((prev: RegistrationCreate) => ({
                        ...prev,
                        photo_release_granted: e.target.checked,
                      }))}
                      className="mt-1 w-4 h-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-2 focus:ring-lsc-rose"
                    />
                    <label htmlFor="photo_release_granted" className="text-sm text-lsc-dark dark:text-lsc-cream/80">
                      {t('registration.field.photoRelease', 'I consent to being photographed at this event.')}
                    </label>
                  </div>
                )}

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
                    className="flex-1 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose disabled:bg-lsc-rose text-white rounded-xl transition-colors flex items-center justify-center gap-2"
                  >
                    {mutation.isPending ? (
                      <>
                        <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                        {t('registration.button.registering', 'Registering...')}
                      </>
                    ) : isFull ? (
                      t('registration.button.joinWaitlist', 'Join Waitlist')
                    ) : (
                      t('registration.button.register', 'Register')
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
