/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CreditCard, CheckCircle, AlertCircle, Clock, User, Mail, MapPin, IdCard, Info } from 'lucide-react'
import { submitCardApplication, CardApplication, CardApplicationCreate } from '@/api/card-applications-api'
import { useTranslation} from '@/i18n'
import { RequiredMark } from '@/components/ui/RequiredMark'
import { TurnstileWidget } from '@/components/TurnstileWidget'
import PageContainer from '@/components/layout/PageContainer'

const US_STATES = [
  { value: 'AL', label: 'Alabama' }, { value: 'AK', label: 'Alaska' }, { value: 'AZ', label: 'Arizona' },
  { value: 'AR', label: 'Arkansas' }, { value: 'CA', label: 'California' }, { value: 'CO', label: 'Colorado' },
  { value: 'CT', label: 'Connecticut' }, { value: 'DE', label: 'Delaware' }, { value: 'FL', label: 'Florida' },
  { value: 'GA', label: 'Georgia' }, { value: 'HI', label: 'Hawaii' }, { value: 'ID', label: 'Idaho' },
  { value: 'IL', label: 'Illinois' }, { value: 'IN', label: 'Indiana' }, { value: 'IA', label: 'Iowa' },
  { value: 'KS', label: 'Kansas' }, { value: 'KY', label: 'Kentucky' }, { value: 'LA', label: 'Louisiana' },
  { value: 'ME', label: 'Maine' }, { value: 'MD', label: 'Maryland' }, { value: 'MA', label: 'Massachusetts' },
  { value: 'MI', label: 'Michigan' }, { value: 'MN', label: 'Minnesota' }, { value: 'MS', label: 'Mississippi' },
  { value: 'MO', label: 'Missouri' }, { value: 'MT', label: 'Montana' }, { value: 'NE', label: 'Nebraska' },
  { value: 'NV', label: 'Nevada' }, { value: 'NH', label: 'New Hampshire' }, { value: 'NJ', label: 'New Jersey' },
  { value: 'NM', label: 'New Mexico' }, { value: 'NY', label: 'New York' }, { value: 'NC', label: 'North Carolina' },
  { value: 'ND', label: 'North Dakota' }, { value: 'OH', label: 'Ohio' }, { value: 'OK', label: 'Oklahoma' },
  { value: 'OR', label: 'Oregon' }, { value: 'PA', label: 'Pennsylvania' }, { value: 'RI', label: 'Rhode Island' },
  { value: 'SC', label: 'South Carolina' }, { value: 'SD', label: 'South Dakota' }, { value: 'TN', label: 'Tennessee' },
  { value: 'TX', label: 'Texas' }, { value: 'UT', label: 'Utah' }, { value: 'VT', label: 'Vermont' },
  { value: 'VA', label: 'Virginia' }, { value: 'WA', label: 'Washington' }, { value: 'WV', label: 'West Virginia' },
  { value: 'WI', label: 'Wisconsin' }, { value: 'WY', label: 'Wyoming' },
]

const ID_TYPES = [
  { value: 'driver_license', label: "Driver's License" },
  { value: 'state_id', label: 'State ID' },
  { value: 'passport', label: 'Passport' },
  { value: 'utility_bill', label: 'Utility Bill' },
  { value: 'other', label: 'Other document' },
]

// NOTE: patron-facing "Check Application Status" tab and its supporting
// StatusBadge / checkEmail / checkedApplication state were removed in
// fix(card-application): the underlying GET /card-applications/check/{email}
// endpoint requires staff auth, so the tab 403'd for the very users it was
// built for. Tracked for token-based re-introduction in issue #1028.

export default function CardApplicationPage(): React.ReactElement {
  const { t } = useTranslation()
  const [formData, setFormData] = useState<CardApplicationCreate>({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    date_of_birth: '',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    zip_code: '',
    id_type: '',
    id_number_last4: '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const [submittedApplication, setSubmittedApplication] = useState<CardApplication | null>(null)
  const [turnstileToken, setTurnstileToken] = useState('')

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ): void => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    setIsSubmitting(true)
    setSubmitStatus('idle')
    setErrorMessage('')

    try {
      const data: CardApplicationCreate = {
        first_name: formData.first_name,
        last_name: formData.last_name,
        email: formData.email,
        address_line1: formData.address_line1,
        city: formData.city,
        state: formData.state,
        zip_code: formData.zip_code,
      }

      if (formData.phone) data.phone = formData.phone
      if (formData.date_of_birth) data.date_of_birth = formData.date_of_birth
      if (formData.address_line2) data.address_line2 = formData.address_line2
      if (formData.id_type) data.id_type = formData.id_type
      if (formData.id_number_last4) data.id_number_last4 = formData.id_number_last4
      if (turnstileToken) data.turnstile_token = turnstileToken

      const application = await submitCardApplication(data)
      setSubmittedApplication(application)
      setSubmitStatus('success')
      setFormData({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        date_of_birth: '',
        address_line1: '',
        address_line2: '',
        city: '',
        state: '',
        zip_code: '',
        id_type: '',
        id_number_last4: '',
      })
    } catch (error: unknown) {
      setSubmitStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'Failed to submit application')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <PageContainer className="space-y-10 py-8">
      {/* Header */}
      <section className="text-center py-6">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-xl bg-lsc-cream dark:bg-earth-800/30 flex items-center justify-center">
            <CreditCard aria-hidden="true" className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <h1 className="text-3xl md:text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Library Card Application
          </h1>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl mx-auto">
          Apply for a free library card and unlock access to our entire collection, digital resources, and programs.
        </p>
      </section>

      {/* Info Banner */}
      <section className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-full bg-earth-100 dark:bg-earth-800/50 flex items-center justify-center flex-shrink-0">
            <Clock aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <div>
            <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">Application Review Process</h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Applications are reviewed by our staff within 1-2 business days. Once approved, you will receive your library card number via email and can pick up your physical card at any branch.
            </p>
          </div>
        </div>
      </section>

      {/* When to create an account — timeline clarity */}
      <section className="bg-sage-50 dark:bg-sage-900/20 border border-sage-200 dark:border-sage-700 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-full bg-sage-100 dark:bg-sage-800/50 flex items-center justify-center flex-shrink-0">
            <Info aria-hidden="true" className="w-5 h-5 text-sage-700 dark:text-sage-400" />
          </div>
          <div>
            <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">When Should I Create an Online Account?</h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              Your library card application and online account are separate. You don't need to wait for card approval to create an account — <strong>you can do both at the same time!</strong>
            </p>
            <ul className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1 list-disc list-inside mb-3">
              <li><strong>Library card</strong> — gives you borrowing privileges at any branch</li>
              <li><strong>Online account</strong> — lets you place holds, renew items, and access digital resources</li>
            </ul>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              We recommend applying for your card here. Online accounts are
              currently invite-only — you can{' '}
              <Link to="/register" className="text-lsc-rose hover:text-lsc-rose/80 font-medium underline">
                join the waiting list
              </Link>{' '}
              and we'll set up your account when your card is approved.
            </p>
          </div>
        </div>
      </section>

      {/* Cross-link: account login/register */}
      <div className="bg-earth-50 dark:bg-earth-800/30 border border-lsc-border dark:border-earth-700 rounded-lg p-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        Already have an account?{' '}
        <Link to="/login" className="text-lsc-rose hover:text-lsc-rose/80 font-medium underline">
          Sign in
        </Link>
        {' | '}
        New here?{' '}
        <Link to="/register" className="text-lsc-rose hover:text-lsc-rose/80 font-medium underline">
          Join the waiting list
        </Link>
        {' | '}
        <Link to="/get-started" className="text-lsc-rose hover:text-lsc-rose/80 font-medium underline">
          New patron? See the full getting started guide
        </Link>
      </div>

      {/* Apply section (the patron-facing "Check Status" tab was removed; see issue #1028) */}
      <>
          {submitStatus === 'success' && submittedApplication ? (
            <section className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl p-8 text-center">
              <div className="w-16 h-16 rounded-full bg-status-success-100 dark:bg-status-success-800/50 flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-status-success-600 dark:text-status-success-400" />
              </div>
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                Application Submitted!
              </h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
                Thank you, {submittedApplication.first_name}! Your library card application has been received. We will review it and notify you at <strong>{submittedApplication.email}</strong> within 1-2 business days.
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
                Application ID: #{submittedApplication.id}
              </p>
              <button
                onClick={() => {
                  setSubmitStatus('idle')
                  setSubmittedApplication(null)
                }}
                className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-xl transition-colors"
              >
                Submit Another Application
              </button>
            </section>
          ) : (
            <section className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
              <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream mb-6">
                Application Form
              </h2>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Personal Information */}
                <fieldset>
                  <legend className="sr-only">Personal Information</legend>
                  <h3 className="flex items-center gap-2 text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-4" aria-hidden="true">
                    <User className="w-5 h-5" />
                    Personal Information
                  </h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="first_name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                        First Name <RequiredMark />
                      </label>
                      <input
                        type="text"
                        id="first_name"
                        name="first_name"
                        required
                        value={formData.first_name}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                        placeholder={t('placeholder.cardApplication.mei')}
                      />
                    </div>
                    <div>
                      <label htmlFor="last_name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                        Last Name <RequiredMark />
                      </label>
                      <input
                        type="text"
                        id="last_name"
                        name="last_name"
                        required
                        value={formData.last_name}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                        placeholder={t('placeholder.cardApplication.chen')}
                      />
                    </div>
                  </div>
                </fieldset>

                {/* Contact Information */}
                <fieldset>
                  <legend className="sr-only">Contact Information</legend>
                  <h3 className="flex items-center gap-2 text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-4" aria-hidden="true">
                    <Mail className="w-5 h-5" />
                    Contact Information
                  </h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="email" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                        Email <RequiredMark />
                      </label>
                      <input
                        type="email"
                        id="email"
                        name="email"
                        required
                        value={formData.email}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                        placeholder={t('placeholder.cardApplication.meichenemailcom')}
                      />
                    </div>
                    <div>
                      <label htmlFor="phone" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                        Phone
                      </label>
                      <input
                        type="tel"
                        id="phone"
                        name="phone"
                        value={formData.phone}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label htmlFor="date_of_birth" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                        Date of Birth
                      </label>
                      <input
                        type="date"
                        id="date_of_birth"
                        name="date_of_birth"
                        value={formData.date_of_birth}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                      />
                    </div>
                  </div>
                </fieldset>

                {/* Address */}
                <fieldset>
                  <legend className="sr-only">Address</legend>
                  <h3 className="flex items-center gap-2 text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-4" aria-hidden="true">
                    <MapPin className="w-5 h-5" />
                    Address
                  </h3>
                  <div className="space-y-4">
                    <div>
                      <label htmlFor="address_line1" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                        Street Address <RequiredMark />
                      </label>
                      <input
                        type="text"
                        id="address_line1"
                        name="address_line1"
                        required
                        value={formData.address_line1}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                        placeholder={t('placeholder.cardApplication.123MainStreet')}
                      />
                    </div>
                    <div>
                      <label htmlFor="address_line2" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                        Apt, Suite, Unit (Optional)
                      </label>
                      <input
                        type="text"
                        id="address_line2"
                        name="address_line2"
                        value={formData.address_line2}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                        placeholder={t('placeholder.cardApplication.apt4b')}
                      />
                    </div>
                    <div className="grid md:grid-cols-3 gap-4">
                      <div>
                        <label htmlFor="city" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                          City <RequiredMark />
                        </label>
                        <input
                          type="text"
                          id="city"
                          name="city"
                          required
                          value={formData.city}
                          onChange={handleInputChange}
                          className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                          placeholder={t('placeholder.cardApplication.yourCity')}
                        />
                      </div>
                      <div>
                        <label htmlFor="state" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                          State <RequiredMark />
                        </label>
                        <select
                          id="state"
                          name="state"
                          required
                          value={formData.state}
                          onChange={handleInputChange}
                          className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                        >
                          <option value="">Select...</option>
                          {US_STATES.map((s) => (
                            <option key={s.value} value={s.value}>{s.label}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label htmlFor="zip_code" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                          ZIP Code <RequiredMark />
                        </label>
                        <input
                          type="text"
                          id="zip_code"
                          name="zip_code"
                          required
                          value={formData.zip_code}
                          onChange={handleInputChange}
                          className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                          placeholder={t('placeholder.cardApplication.12345')}
                        />
                      </div>
                    </div>
                  </div>
                </fieldset>

                {/* ID Verification (Optional) */}
                <fieldset>
                  <legend className="sr-only">ID Verification (Optional)</legend>
                  <h3 className="flex items-center gap-2 text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-4" aria-hidden="true">
                    <IdCard className="w-5 h-5" />
                    ID Verification (Optional)
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                    Providing ID information can speed up your application review.
                  </p>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="id_type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                        ID Type
                      </label>
                      <select
                        id="id_type"
                        name="id_type"
                        value={formData.id_type}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                      >
                        <option value="">Select...</option>
                        {ID_TYPES.map((t) => (
                          <option key={t.value} value={t.value}>{t.label}</option>
                        ))}
                      </select>
                      {formData.id_type === 'other' && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
                          We accept many documents — if yours isn't listed, apply and a staff member will follow up.
                        </p>
                      )}
                    </div>
                    <div>
                      <label htmlFor="id_number_last4" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                        Last 4 Digits of ID
                      </label>
                      <input
                        type="text"
                        id="id_number_last4"
                        name="id_number_last4"
                        maxLength={4}
                        value={formData.id_number_last4}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                        placeholder={t('placeholder.cardApplication.1234')}
                      />
                    </div>
                  </div>
                </fieldset>

                {/* Error Message */}
                {submitStatus === 'error' && (
                  <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
                    <p className="text-status-danger-700 dark:text-status-danger-400">{errorMessage}</p>
                  </div>
                )}

                <TurnstileWidget onVerify={setTurnstileToken} />

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isSubmitting || !turnstileToken}
                  className="w-full inline-flex items-center justify-center gap-2 px-6 py-4 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white font-medium rounded-xl transition-colors"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full motion-safe:animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <CreditCard className="w-5 h-5" />
                      Submit Application
                    </>
                  )}
                </button>
              </form>
            </section>
          )}
        </>

      {/* Already have an account? */}
      <section className="text-center py-4">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Already have an account?{' '}
          <Link to="/login" className="text-lsc-rose hover:text-lsc-rose/80 font-medium underline decoration-lsc-rose/30 hover:decoration-lsc-rose transition-colors">
            Sign in here
          </Link>
        </p>
      </section>
    </PageContainer>
  )
}
