/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Phone,
  Mail,
  MapPin,
  Clock,
  MessageCircle,
  HelpCircle,
  Send,
  Car,
  Navigation,
  ArrowRight,
  AlertTriangle,
  Heart,
  CheckCircle2,
  Baby,
} from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import QuickContactCard from '@/components/QuickContactCard'
import { useTranslation } from '@/i18n'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useBranding } from '@/contexts/BrandingContext'
import { submitContactMessage, type SupportTicketResponse } from '@/api/support-api'
import { TurnstileWidget } from '@/components/TurnstileWidget'

type SubjectGroup = 'help' | 'borrow' | 'youth' | 'civic' | 'concern' | 'other'

interface SubjectOption {
  key: string
  group: SubjectGroup
}

const SUBJECT_OPTIONS: SubjectOption[] = [
  { key: 'referenceHelp', group: 'help' },
  { key: 'websiteBug', group: 'help' },
  { key: 'accountCard', group: 'borrow' },
  { key: 'interlibraryLoan', group: 'borrow' },
  { key: 'suggestPurchase', group: 'borrow' },
  { key: 'programsEvents', group: 'borrow' },
  { key: 'youthFamily', group: 'youth' },
  { key: 'teens', group: 'youth' },
  { key: 'accessibility', group: 'civic' },
  { key: 'discrimination', group: 'civic' },
  { key: 'recordsRequest', group: 'civic' },
  { key: 'board', group: 'civic' },
  { key: 'donation', group: 'civic' },
  { key: 'bookConcern', group: 'concern' },
  { key: 'other', group: 'other' },
]

const ANONYMOUS_ALLOWED = new Set(['bookConcern', 'discrimination', 'accessibility', 'other'])

type AgeGroup = 'adult' | 'teen' | 'kid'
type ContactMethod = 'email' | 'phone' | 'text' | 'visit' | 'none'

interface FieldErrors {
  category?: string
  message?: string
  name?: string
  email?: string
  phone?: string
}

export default function ContactPage(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  usePageTitle(t('contact.pageTitle'))

  const [selectedGroup, setSelectedGroup] = useState<SubjectGroup | ''>('')
  const [formData, setFormData] = useState({
    category: '',
    name: '',
    email: '',
    phone: '',
    message: '',
    contactMethod: 'email' as ContactMethod,
    ageGroup: 'adult' as AgeGroup,
    isAnonymous: false,
    // honeypot field -- bots fill it, humans don't
    website: '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const [ticket, setTicket] = useState<SupportTicketResponse | null>(null)
  const [turnstileToken, setTurnstileToken] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [showErrorSummary, setShowErrorSummary] = useState(false)

  const receiptRef = useRef<HTMLDivElement>(null)
  const errorSummaryRef = useRef<HTMLDivElement>(null)

  const isKidPath = formData.ageGroup === 'kid'
  const category = formData.category
  const isAnonymousAllowed = ANONYMOUS_ALLOWED.has(category)
  const effectiveAnonymous = isKidPath || (isAnonymousAllowed && formData.isAnonymous)
  const isRecordsRequest = !isKidPath && category === 'recordsRequest'

  // Filter subject options by selected group (or all if none picked yet)
  const visibleOptions = useMemo(
    () => (selectedGroup ? SUBJECT_OPTIONS.filter((o) => o.group === selectedGroup) : []),
    [selectedGroup]
  )

  useEffect(() => {
    if (submitStatus === 'success' && receiptRef.current) {
      receiptRef.current.focus()
    }
  }, [submitStatus])

  useEffect(() => {
    if (showErrorSummary && errorSummaryRef.current) {
      errorSummaryRef.current.focus()
    }
  }, [showErrorSummary])

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ): void => {
    const { name, value, type } = e.target
    const checked = (e.target as HTMLInputElement).checked
    setFormData((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
    // Clear field error on edit
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }))
  }

  const handleGroupChange = (g: SubjectGroup): void => {
    setSelectedGroup(g)
    setFormData((prev) => ({ ...prev, category: '' }))
  }

  function validate(): FieldErrors {
    const errs: FieldErrors = {}
    if (!isKidPath && !formData.category) {
      errs.category = t('contact.errorMissingTopic')
    }
    if (!formData.message.trim()) {
      errs.message = t('contact.errorMissingMessage')
    }
    if (!effectiveAnonymous) {
      if (formData.contactMethod === 'email' && !formData.email.trim()) {
        errs.email = t('contact.errorMissingEmail')
      }
      if ((formData.contactMethod === 'phone' || formData.contactMethod === 'text') && !formData.phone.trim()) {
        errs.phone = t('contact.errorMissingPhone')
      }
      if (
        formData.contactMethod !== 'none' &&
        formData.contactMethod !== 'visit' &&
        !formData.name.trim()
      ) {
        errs.name = t('contact.errorMissingName')
      }
    }
    return errs
  }

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    setSubmitStatus('idle')
    setErrorMessage('')

    // Skip frontend-side validation when the honeypot is filled. We still
    // forward the request to the backend (honeypot field passes through as
    // `websiteUrl`), so the server can log the IP and return a fake ack.
    const honeypotTripped = Boolean(formData.website)

    if (!honeypotTripped) {
      const errs = validate()
      if (Object.values(errs).some(Boolean)) {
        setFieldErrors(errs)
        setShowErrorSummary(true)
        return
      }
      setShowErrorSummary(false)
      setFieldErrors({})
    }

    setIsSubmitting(true)
    try {
      const effectiveCategory = isKidPath ? 'youthFamily' : category
      const effectiveMethod: ContactMethod = isKidPath ? 'none' : formData.contactMethod
      const sendName = effectiveAnonymous ? undefined : formData.name.trim() || undefined
      const sendEmail = effectiveAnonymous || effectiveMethod === 'none' || effectiveMethod === 'visit'
        ? undefined
        : formData.email.trim() || undefined
      const sendPhone = effectiveAnonymous ? undefined : formData.phone.trim() || undefined

      const apiMethod: 'email' | 'phone' | 'visit' | 'none' =
        effectiveMethod === 'text' ? 'phone' : effectiveMethod

      const res = await submitContactMessage({
        name: sendName,
        email: sendEmail,
        phone: sendPhone,
        issueDescription: formData.message.trim(),
        contactMethod: apiMethod,
        category: effectiveCategory,
        isAnonymous: effectiveAnonymous,
        websiteUrl: formData.website || undefined,
        turnstileToken: turnstileToken || undefined,
        timestamp: new Date().toISOString(),
      })
      setTicket(res)
      setSubmitStatus('success')
      setFormData((prev) => ({
        ...prev,
        category: '',
        name: '',
        email: '',
        phone: '',
        message: '',
      }))
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : t('contact.errorMessage', { phone: branding.phone || '' })
      )
      setSubmitStatus('error')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReset = (): void => {
    setSubmitStatus('idle')
    setTicket(null)
    setSelectedGroup('')
  }

  // ====== Render branches ======

  // Receipt branch (after successful submit)
  if (submitStatus === 'success' && ticket) {
    return (
      <StandardPageLayout
        title={t('contact.pageTitle')}
        subtitle={t('contact.haveAQuestionOrFeedback')}
        icon={MessageCircle}
      >
        <section
          ref={receiptRef}
          tabIndex={-1}
          role="status"
          aria-live="polite"
          className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl p-6 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
        >
          <div className="flex items-start gap-3 mb-4">
            <CheckCircle2 aria-hidden="true" className="w-6 h-6 text-status-success-700 dark:text-status-success-400 flex-shrink-0 mt-1" />
            <div>
              <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream">
                {t('contact.ticketReceiptHeading')}
              </h2>
              <p className="text-lsc-dark/80 dark:text-lsc-cream/80 mt-1">
                {t('contact.ticketReceiptIntro')}
              </p>
            </div>
          </div>

          <dl className="space-y-2 mb-4 text-lsc-dark dark:text-lsc-cream">
            <div className="flex gap-2">
              <dt className="font-medium">{t('contact.ticketReferenceLabel')}:</dt>
              <dd className="font-mono">{ticket.reference_number}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="font-medium">{t('contact.ticketResponseWindowLabel')}:</dt>
              <dd>{describeSla(ticket, t)}</dd>
            </div>
          </dl>

          <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-3 mb-4">
            <p className="text-sm text-lsc-dark dark:text-lsc-cream flex items-start gap-2">
              <AlertTriangle aria-hidden="true" className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>
                {t('contact.ticketUrgentCallout', { phone: branding.phone || '' })}
              </span>
            </p>
          </div>

          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-xl transition-colors"
          >
            {t('contact.sendAnother')}
          </button>
        </section>
      </StandardPageLayout>
    )
  }

  return (
    <StandardPageLayout
      title={t('contact.pageTitle')}
      subtitle={t('contact.haveAQuestionOrFeedback')}
      icon={MessageCircle}
    >
      {/* Crisis Resources Strip -- always visible, calm tone */}
      <section
        aria-labelledby="crisis-heading"
        className="bg-earth-50 dark:bg-earth-800/30 border-l-4 border-status-warning-500 rounded-r-xl p-5"
      >
        <h2
          id="crisis-heading"
          className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2"
        >
          <Heart aria-hidden="true" className="w-5 h-5 text-status-warning-600" />
          {t('contact.crisisStripHeading')}
        </h2>
        <ul className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 space-y-1">
          <li><a className="hover:underline" href="tel:911"><strong>{t('contact.crisisEmergency')}</strong></a></li>
          <li><a className="hover:underline" href="tel:988"><strong>{t('contact.crisisMentalHealth')}</strong></a></li>
          <li><strong>{t('contact.crisisTextLine')}</strong></li>
          <li><a className="hover:underline" href="tel:18004224453"><strong>{t('contact.crisisChildhelp')}</strong></a></li>
          <li><a className="hover:underline" href="tel:18664887386"><strong>{t('contact.crisisTrevor')}</strong></a></li>
        </ul>
      </section>

      {/* Quick Help Banner */}
      <section className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-full bg-earth-100 dark:bg-earth-800/50 flex items-center justify-center flex-shrink-0">
            <HelpCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <div>
            <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('contact.systemStatus')}</h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              {t('contact.systemStatusText1')} <a href="/status" className="text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium">{t('contact.systemStatusPage')}</a> {t('contact.systemStatusText2')}
            </p>
            <a href="/status" className="inline-flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium text-sm">
              {t('contact.viewSystemStatus')} <ArrowRight aria-hidden="true" className="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      {/* Quick Numbers */}
      <QuickContactCard />

      {/* Contact Info Cards */}
      <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {/* Phone */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="w-10 h-10 rounded-xl bg-lsc-cream dark:bg-lsc-brown/30 flex items-center justify-center mb-4">
            <Phone aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('contact.phone')}</h2>
          {branding.phone && (
            <a
              href={`tel:${branding.phone.replace(/\D/g, '')}`}
              className="text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:hover:text-brand-300 font-medium"
            >
              {branding.phone}
            </a>
          )}
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {t('contact.phoneHoursMonThu')}<br />
            {t('contact.phoneHoursFriSat')}<br />
            {t('contact.phoneHoursSun')}
          </p>
          <div className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700">
            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{t('contact.relay711Heading')}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {t('contact.relay711Body', { phone: branding.phone || '' })}
            </p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {t('contact.relayVrsBody', { phone: branding.phone || '' })}
            </p>
          </div>
        </div>

        {/* Email */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="w-10 h-10 rounded-xl bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center mb-4">
            <Mail aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </div>
          <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('contact.email')}</h2>
          {branding.contact_email && (
            <a
              href={`mailto:${branding.contact_email}`}
              className="text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:hover:text-brand-300 font-medium"
            >
              {branding.contact_email}
            </a>
          )}
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {t('contact.emailResponseTime')}
          </p>
        </div>

        {/* Address */}
        <AddressCard />

        {/* Kids & Teens */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
          <div className="w-10 h-10 rounded-xl bg-lsc-cream dark:bg-lsc-brown/30 flex items-center justify-center mb-4">
            <Baby aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
            {t('contact.youthCardHeading')}
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            {t('contact.youthCardBody')}
          </p>
          <button
            type="button"
            onClick={() => setFormData((prev) => ({ ...prev, ageGroup: 'kid' }))}
            className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium"
          >
            {t('contact.youthCardLinkText')}
          </button>
        </div>
      </section>

      {/* Hours link */}
      <div className="flex items-center gap-2 px-2">
        <Clock aria-hidden="true" className="w-4 h-4 text-lsc-rose" />
        <Link to="/branches" className="text-sm text-lsc-rose hover:underline font-medium">
          {t('contact.viewHoursAndLocations')}
        </Link>
      </div>

      {/* Contact Form */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream mb-2">
          {t('contact.sendMessage')}
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">{t('contact.formIntro')}</p>

        {/* Error Summary -- GOV.UK pattern */}
        {showErrorSummary && (
          <div
            ref={errorSummaryRef}
            tabIndex={-1}
            role="alert"
            className="mb-6 p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-300 dark:border-status-danger-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-status-danger-500"
          >
            <h3 className="font-bold text-status-danger-700 dark:text-status-danger-300 mb-2">
              {t('contact.errorSummaryHeading')}
            </h3>
            <ul className="list-disc pl-5 space-y-1 text-sm">
              {fieldErrors.category && <li><a href="#contact-group-fieldset" className="underline">{fieldErrors.category}</a></li>}
              {fieldErrors.name && <li><a href="#contact-name" className="underline">{fieldErrors.name}</a></li>}
              {fieldErrors.email && <li><a href="#contact-email" className="underline">{fieldErrors.email}</a></li>}
              {fieldErrors.phone && <li><a href="#contact-phone" className="underline">{fieldErrors.phone}</a></li>}
              {fieldErrors.message && <li><a href="#contact-message" className="underline">{fieldErrors.message}</a></li>}
            </ul>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6" noValidate>
          {/* Honeypot -- visually hidden, off-screen */}
          <div className="sr-only" aria-hidden="true">
            <label htmlFor="contact-website">Website</label>
            <input
              type="text"
              id="contact-website"
              name="website"
              value={formData.website}
              onChange={handleInputChange}
              tabIndex={-1}
              autoComplete="off"
            />
          </div>

          {/* Age-group + anonymous (COPPA-safe / sensitive routing) */}
          <fieldset>
            <legend className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
              {t('contact.ageGroupLegend')}
            </legend>
            <div className="flex flex-wrap gap-4">
              {(['adult', 'teen', 'kid'] as AgeGroup[]).map((g) => (
                <label key={g} className="inline-flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                  <input
                    type="radio"
                    name="ageGroup"
                    value={g}
                    checked={formData.ageGroup === g}
                    onChange={handleInputChange}
                    className="w-4 h-4 text-lsc-rose focus:ring-lsc-rose"
                  />
                  {t(`contact.ageGroup${g.charAt(0).toUpperCase()}${g.slice(1)}`)}
                </label>
              ))}
            </div>
          </fieldset>

          {isKidPath ? (
            <>
              {/* COPPA-safe path: no name, no email, no phone, no category picker */}
              <div className="bg-earth-50 dark:bg-earth-800/30 rounded-lg p-4">
                <h3 className="font-bold text-lsc-dark dark:text-lsc-cream mb-1">{t('contact.kidPathHeading')}</h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('contact.kidPathIntro')}</p>
              </div>
              <div>
                <label htmlFor="contact-message" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                  {t('contact.kidPathMessageLabel')} <span className="text-status-danger-500"><span className="sr-only">{t('contact.requiredSrLabel')}</span>*</span>
                </label>
                <textarea
                  id="contact-message"
                  name="message"
                  required
                  rows={5}
                  value={formData.message}
                  onChange={handleInputChange}
                  aria-required="true"
                  aria-describedby="contact-message-err"
                  aria-invalid={Boolean(fieldErrors.message)}
                  className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent transition-colors resize-none"
                />
                <p id="contact-message-err" className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-1">
                  {fieldErrors.message || ''}
                </p>
              </div>
            </>
          ) : (
            <>
              {/* Two-step topic picker (group -> specific) */}
              <fieldset id="contact-group-fieldset">
                <legend className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                  {t('contact.subjectGroupLegend')} <span className="text-status-danger-500"><span className="sr-only">{t('contact.requiredSrLabel')}</span>*</span>
                </legend>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{t('contact.subjectGroupHelp')}</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {(['help', 'borrow', 'youth', 'civic', 'concern', 'other'] as SubjectGroup[]).map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => handleGroupChange(g)}
                      aria-pressed={selectedGroup === g}
                      className={
                        'px-4 py-3 rounded-xl border-2 text-sm font-medium text-left transition-colors min-h-[44px] ' +
                        (selectedGroup === g
                          ? 'border-lsc-rose bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream'
                          : 'border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/40 dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream')
                      }
                    >
                      {t(`contact.subjectGroups.${g}`)}
                    </button>
                  ))}
                </div>
                {fieldErrors.category && (
                  <p className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-2">{fieldErrors.category}</p>
                )}
              </fieldset>

              {/* Specific category */}
              {selectedGroup && (
                <div>
                  <label htmlFor="contact-category" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                    {t('contact.subjectLabel')} <span className="text-status-danger-500"><span className="sr-only">{t('contact.requiredSrLabel')}</span>*</span>
                  </label>
                  <select
                    id="contact-category"
                    name="category"
                    required
                    value={formData.category}
                    onChange={handleInputChange}
                    aria-required="true"
                    aria-invalid={Boolean(fieldErrors.category)}
                    aria-describedby="contact-category-err"
                    className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent transition-colors"
                  >
                    <option value="">{t('contact.selectSubject')}</option>
                    {visibleOptions.map((opt) => (
                      <option key={opt.key} value={opt.key}>{t(`contact.subjectOptions.${opt.key}`)}</option>
                    ))}
                  </select>
                  <p id="contact-category-err" className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-1">
                    {fieldErrors.category || ''}
                  </p>
                </div>
              )}

              {/* Records-request redirect: short-circuits to dedicated FOIA intake */}
              {isRecordsRequest && (
                <div
                  data-testid="contact-records-redirect"
                  className="bg-earth-50 dark:bg-earth-800/30 border-l-4 border-lsc-rose rounded-r-lg p-4"
                >
                  <h3 className="font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                    {t('contact.recordsRedirectHeading', 'Public records requests have their own form')}
                  </h3>
                  <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mb-4">
                    {t(
                      'contact.recordsRedirectBody',
                      'Public records requests use a dedicated intake form to satisfy Ohio R.C. 149.43. It captures the records, time period, and delivery format, and routes to our records officer.'
                    )}
                  </p>
                  <Link
                    to="/transparency/records-requests"
                    className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-xl transition-colors min-h-[44px]"
                  >
                    {t('contact.recordsRedirectCta', 'Go to records request form')}
                    <ArrowRight aria-hidden="true" className="w-4 h-4" />
                  </Link>
                </div>
              )}

              {!isRecordsRequest && (
                <>
              {/* Anonymous toggle (visible for sensitive categories) */}
              {isAnonymousAllowed && (
                <div className="bg-earth-50 dark:bg-earth-800/30 rounded-lg p-4">
                  <label className="inline-flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      name="isAnonymous"
                      checked={formData.isAnonymous}
                      onChange={handleInputChange}
                      className="w-4 h-4 mt-1 text-lsc-rose focus:ring-lsc-rose"
                    />
                    <span>
                      <span className="font-medium text-lsc-dark dark:text-lsc-cream">{t('contact.anonymousToggleLabel')}</span>
                      <span className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {t('contact.anonymousToggleHelp')}
                      </span>
                    </span>
                  </label>
                </div>
              )}

              {/* Preferred contact method */}
              {!effectiveAnonymous && (
                <fieldset>
                  <legend className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                    {t('contact.preferredContactLegend')}
                  </legend>
                  <div className="flex flex-wrap gap-4">
                    {(['email', 'phone', 'text', 'visit', 'none'] as ContactMethod[]).map((m) => (
                      <label key={m} className="inline-flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                        <input
                          type="radio"
                          name="contactMethod"
                          value={m}
                          checked={formData.contactMethod === m}
                          onChange={handleInputChange}
                          className="w-4 h-4 text-lsc-rose focus:ring-lsc-rose"
                        />
                        {t(`contact.preferredContact${m.charAt(0).toUpperCase()}${m.slice(1)}`)}
                      </label>
                    ))}
                  </div>
                </fieldset>
              )}

              {/* Name + Email + Phone -- visible labels above each */}
              {!effectiveAnonymous && (
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <label htmlFor="contact-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                      {t('contact.nameLabel')}{formData.contactMethod !== 'none' && formData.contactMethod !== 'visit' && (
                        <> <span className="text-status-danger-500"><span className="sr-only">{t('contact.requiredSrLabel')}</span>*</span></>
                      )}
                    </label>
                    <input
                      type="text"
                      id="contact-name"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      aria-invalid={Boolean(fieldErrors.name)}
                      aria-describedby="contact-name-err"
                      autoComplete="name"
                      className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-600 dark:placeholder-earth-400 focus:ring-2 focus:ring-lsc-rose focus:border-transparent transition-colors"
                    />
                    <p id="contact-name-err" className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-1">
                      {fieldErrors.name || ''}
                    </p>
                  </div>

                  <div>
                    <label htmlFor="contact-email" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                      {t('contact.emailLabel')}
                      {formData.contactMethod === 'email' && (
                        <> <span className="text-status-danger-500"><span className="sr-only">{t('contact.requiredSrLabel')}</span>*</span></>
                      )}
                    </label>
                    <input
                      type="email"
                      id="contact-email"
                      name="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      aria-invalid={Boolean(fieldErrors.email)}
                      aria-describedby="contact-email-err"
                      autoComplete="email"
                      className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-600 dark:placeholder-earth-400 focus:ring-2 focus:ring-lsc-rose focus:border-transparent transition-colors"
                    />
                    <p id="contact-email-err" className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-1">
                      {fieldErrors.email || ''}
                    </p>
                  </div>

                  {(formData.contactMethod === 'phone' || formData.contactMethod === 'text') && (
                    <div className="md:col-span-2">
                      <label htmlFor="contact-phone" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                        {t('contact.phoneLabel')} <span className="text-status-danger-500"><span className="sr-only">{t('contact.requiredSrLabel')}</span>*</span>
                      </label>
                      <input
                        type="tel"
                        id="contact-phone"
                        name="phone"
                        value={formData.phone}
                        onChange={handleInputChange}
                        aria-invalid={Boolean(fieldErrors.phone)}
                        aria-describedby="contact-phone-err"
                        placeholder={t('contact.phonePlaceholder')}
                        autoComplete="tel"
                        className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-600 dark:placeholder-earth-400 focus:ring-2 focus:ring-lsc-rose focus:border-transparent transition-colors"
                      />
                      <p id="contact-phone-err" className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-1">
                        {fieldErrors.phone || ''}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Message */}
              <div>
                <label htmlFor="contact-message" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                  {t('contact.messageLabel')} <span className="text-status-danger-500"><span className="sr-only">{t('contact.requiredSrLabel')}</span>*</span>
                </label>
                <textarea
                  id="contact-message"
                  name="message"
                  required
                  rows={5}
                  value={formData.message}
                  onChange={handleInputChange}
                  aria-required="true"
                  aria-invalid={Boolean(fieldErrors.message)}
                  aria-describedby="contact-message-err"
                  className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-600 dark:placeholder-earth-400 focus:ring-2 focus:ring-lsc-rose focus:border-transparent transition-colors resize-none"
                  placeholder={t('contact.howCanWeHelpYou')}
                />
                <p id="contact-message-err" className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-1">
                  {fieldErrors.message || ''}
                </p>
              </div>
                </>
              )}
            </>
          )}

          {/* Public records notice */}
          {!isKidPath && !isRecordsRequest && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 border-l-4 border-lsc-rose/50 pl-3">
              {t('contact.publicRecordsNotice')}
            </p>
          )}

          {submitStatus === 'error' && (
            <div
              role="alert"
              className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl"
            >
              <p className="text-status-danger-700 dark:text-status-danger-400 font-medium">
                {errorMessage || t('contact.errorMessage', { phone: branding.phone || '' })}
              </p>
            </div>
          )}

          {!isRecordsRequest && (
            <div className="space-y-4">
              <TurnstileWidget onVerify={setTurnstileToken} />
            <button
              type="submit"
              disabled={isSubmitting || !turnstileToken}
              className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose disabled:opacity-60 text-white font-medium rounded-xl transition-colors min-h-[44px]"
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full motion-safe:animate-spin" />
                  {t('contact.sending')}
                </>
              ) : (
                <>
                  <Send aria-hidden="true" className="w-5 h-5" />
                  {t('contact.sendMessageBtn')}
                </>
              )}
            </button>
            </div>
          )}
        </form>
      </section>

      {/* Help center link */}
      <div className="flex items-center gap-2 px-2">
        <HelpCircle aria-hidden="true" className="w-4 h-4 text-lsc-rose" />
        <Link to="/help" className="text-sm text-lsc-rose hover:underline font-medium">
          {t('contact.browseHelpCenter')}
        </Link>
      </div>

      {/* Directions Section */}
      <section className="bg-gradient-to-br from-lsc-cream to-lsc-cream dark:from-earth-800 dark:to-earth-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-6">
          <Navigation aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream">
            {t('contact.gettingHere')}
          </h2>
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">{t('contact.directions')}</h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              {t('contact.directionsText')}
            </p>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              <strong>{t('contact.fromHighwayBold')}</strong> {t('contact.fromHighwayText')}
            </p>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Car aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{t('contact.parking')}</h3>
            </div>
            <ul className="space-y-2 text-lsc-dark/70 dark:text-lsc-cream/70">
              <li className="flex items-start gap-2">
                <span className="w-2 h-2 rounded-full bg-lsc-rose mt-2 flex-shrink-0" />
                <span><strong>{t('contact.parkingLotBold')}</strong> {t('contact.parkingLotText')}</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-2 h-2 rounded-full bg-lsc-rose mt-2 flex-shrink-0" />
                <span><strong>{t('contact.streetParkingBold')}</strong> {t('contact.streetParkingText')}</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-2 h-2 rounded-full bg-lsc-rose mt-2 flex-shrink-0" />
                <span><strong>{t('contact.bikeRacksBold')}</strong> {t('contact.bikeRacksText')}</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-2 h-2 rounded-full bg-lsc-rose mt-2 flex-shrink-0" />
                <span><strong>{t('contact.busStopBold')}</strong> {t('contact.busStopText')}</span>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </StandardPageLayout>
  )
}

// -- Helpers --

function AddressCard(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  const hasAddress = Boolean(branding.address_line1)
  const cityLine = [branding.city, branding.state, branding.zip_code].filter(Boolean).join(' ')
  const fullAddress = [branding.address_line1, branding.address_line2, cityLine].filter(Boolean).join(', ')
  const mapsUrl = hasAddress
    ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(fullAddress)}`
    : null

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
      <div className="w-10 h-10 rounded-xl bg-lsc-cream dark:bg-earth-800/30 flex items-center justify-center mb-4">
        <MapPin aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
      </div>
      <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('contact.address')}</h2>
      {hasAddress ? (
        <>
          <address className="not-italic text-lsc-dark/80 dark:text-lsc-cream/80 text-sm leading-relaxed">
            {branding.address_line1}<br />
            {branding.address_line2 && <>{branding.address_line2}<br /></>}
            {cityLine && <>{cityLine}</>}
          </address>
          {mapsUrl && (
            <a
              href={mapsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium mt-2"
            >
              {t('contact.getDirections')} <ArrowRight aria-hidden="true" className="w-3 h-3" />
            </a>
          )}
        </>
      ) : (
        <p
          className="text-sm text-status-warning-700 dark:text-status-warning-300 italic"
          role="status"
        >
          {t('contact.addressPending')}
        </p>
      )}
    </div>
  )
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function describeSla(ticket: SupportTicketResponse, t: any): string {
  if (ticket.category === 'suggestPurchase') return t('contact.ticketResponseAcquisitions')
  if (ticket.category === 'accessibility' || ticket.category === 'discrimination') return t('contact.ticketResponseADA')
  const days = ticket.sla_business_days ?? 2
  return t('contact.ticketResponseDays', { days: String(days) })
}
