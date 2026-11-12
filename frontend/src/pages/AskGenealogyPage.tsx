/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState } from 'react'
import { MessageCircle, CheckCircle2, AlertCircle, Loader } from 'lucide-react'
import toast from 'react-hot-toast'
import { clsx } from '@/utils/helpers'
import { fetchApi } from '@/api/fetchApi'
import { useTranslation } from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'
import { RequiredMark } from '@/components/ui/RequiredMark'

export default function AskGenealogyPage(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    preferredContact: 'email',
    researchType: '',
    description: '',
    currentChallenges: '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      await fetchApi('/genealogy/inquiries', {
        method: 'POST',
        body: JSON.stringify({
          first_name: formData.firstName,
          last_name: formData.lastName,
          email: formData.email,
          phone: formData.phone || null,
          preferred_contact: formData.preferredContact,
          research_topic: formData.researchType,
          description: formData.description,
          current_challenges: formData.currentChallenges || null,
        }),
      })

      setIsSubmitting(false)
      setSubmitted(true)
      toast.success(t('askGenealogy.yourQuestionHasBeenSubmitted'))
      setFormData({
        firstName: '',
        lastName: '',
        email: '',
        phone: '',
        preferredContact: 'email',
        researchType: '',
        description: '',
        currentChallenges: '',
      })

      // Reset form after 3 seconds
      setTimeout(() => {
        setSubmitted(false)
      }, 3000)
    } catch (error: unknown) {
      setIsSubmitting(false)
      toast.error(t('askGenealogy.failedToSubmitYourQuestion'))
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }

  if (submitted) {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Success Message */}
        <div className="bg-status-success-50 dark:bg-status-success-900/20 border-2 border-status-success-200 dark:border-status-success-800 rounded-xl p-8 text-center">
          <div className="flex justify-center mb-4">
            <CheckCircle2 className="w-12 h-12 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
          </div>
          <h2 className="text-2xl font-serif font-bold text-status-success-900 dark:text-status-success-100 mb-2">
            Thank You!
          </h2>
          <p className="text-status-success-800 dark:text-status-success-200 mb-4">
            Your question has been submitted successfully.
          </p>
          <p className="text-status-success-700 dark:text-status-success-300 mb-6">
            Our local history and genealogy staff will respond to you within <strong>2 business days</strong> using your preferred contact method.
          </p>
          <button
            onClick={() => setSubmitted(false)}
            className="px-6 py-2 bg-status-success-600 hover:bg-status-success-700 text-white rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-status-success-600 focus:ring-offset-2 dark:focus:ring-offset-earth-800"
          >
            Ask Another Question
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8 max-w-2xl mx-auto">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 rounded-full bg-lsc-rose/10 flex items-center justify-center">
            <MessageCircle className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          </div>
        </div>
        <h1 className="text-3xl md:text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Ask a Genealogist
        </h1>
        <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70">
          Get expert help from our local history and genealogy staff.
        </p>
      </div>

      {/* About the Desk */}
      <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream text-lg mb-2">
          Local History & Genealogy Desk
        </h2>
        <p className="text-lsc-dark/80 dark:text-lsc-cream/80">
          Our staff can help patrons navigate historical records, develop family trees, and connect with ancestors through local archives.
        </p>
      </div>

      {/* What We Can Help With */}
      <div className="space-y-4">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          We Can Help With
        </h2>
        <div className="grid md:grid-cols-2 gap-4">
          {[
            'Getting started with genealogy',
            'Finding ancestors in records',
            'Understanding historical context',
            'Locating local archives',
            'Using Ancestry and FamilySearch',
            'Overcoming research roadblocks',
            'Organizing your findings',
            'DNA results interpretation',
          ].map((topic, idx) => (
            <div key={idx} className="flex items-start gap-3 p-3 bg-lsc-cream/50 dark:bg-earth-700/30 rounded-lg">
              <CheckCircle2 className="w-5 h-5 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <span className="text-lsc-dark/80 dark:text-lsc-cream/80">{topic}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Contact Form */}
      <form onSubmit={handleSubmit} className="space-y-6 bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Your Information
        </h2>

        {/* Name Fields */}
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="firstName" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              First Name <RequiredMark />
            </label>
            <input
              type="text"
              id="firstName"
              name="firstName"
              value={formData.firstName}
              onChange={handleChange}
              required
              aria-required="true"
              className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            />
          </div>
          <div>
            <label htmlFor="lastName" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Last Name <RequiredMark />
            </label>
            <input
              type="text"
              id="lastName"
              name="lastName"
              value={formData.lastName}
              onChange={handleChange}
              required
              aria-required="true"
              className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            />
          </div>
        </div>

        {/* Contact Info */}
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Email <RequiredMark />
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              aria-required="true"
              aria-describedby="email-help"
              className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            />
            <p id="email-help" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              We'll use this to respond to your question
            </p>
          </div>
          <div>
            <label htmlFor="phone" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Phone (Optional)
            </label>
            <input
              type="tel"
              id="phone"
              name="phone"
              value={formData.phone}
              onChange={handleChange}
              className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            />
          </div>
        </div>

        {/* Preferred Contact */}
        <div>
          <label htmlFor="preferredContact" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            How should we contact you?
          </label>
          <select
            id="preferredContact"
            name="preferredContact"
            value={formData.preferredContact}
            onChange={handleChange}
            className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          >
            <option value="email">Email (preferred)</option>
            <option value="phone">Phone</option>
            <option value="either">{t('askGenealogy.eitherWorksForMe')}</option>
          </select>
        </div>

        {/* Your Question */}
        <div className="border-t border-lsc-border dark:border-earth-700 pt-6">
          <h3 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Your Research Question
          </h3>

          <div className="space-y-4">
            <div>
              <label htmlFor="researchType" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                What kind of research help do you need? <RequiredMark />
              </label>
              <select
                id="researchType"
                name="researchType"
                value={formData.researchType}
                onChange={handleChange}
                required
                aria-required="true"
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="">-- Select a topic --</option>
                <option value="getting-started">Getting Started</option>
                <option value="vital-records">{t('askGenealogy.vitalRecordsBirthMarriageDeath')}</option>
                <option value="census">Census Records</option>
                <option value="immigration">Immigration &amp; Naturalization</option>
                <option value="dna">DNA Testing</option>
                <option value="local-resources">Local Resources</option>
                <option value="using-databases">{t('askGenealogy.usingAncestryOrFamilysearch')}</option>
                <option value="roadblock">{t('askGenealogy.iMStuckGenealogyRoadblock')}</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Your Question or Details <RequiredMark />
              </label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                required
                aria-required="true"
                rows={5}
                placeholder="Tell us about your research question. Include details like: What are you trying to find? What have you already tried? What time period or location are you researching?"
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose resize-none"
              />
            </div>

            <div>
              <label htmlFor="currentChallenges" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                What's been your biggest challenge so far? (Optional)
              </label>
              <textarea
                id="currentChallenges"
                name="currentChallenges"
                value={formData.currentChallenges}
                onChange={handleChange}
                rows={3}
                placeholder="Help us understand what's been difficult — this helps us give better advice."
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose resize-none"
              />
            </div>
          </div>
        </div>

        {/* Accessibility Notice */}
        <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-4 flex gap-3">
          <AlertCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-sm text-earth-900 dark:text-earth-200">
            <strong>Accessibility:</strong> Need extra time or prefer a different format? Email {branding.contact_email} directly and let us know how we can help.
          </p>
        </div>

        {/* Submit Button */}
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isSubmitting}
            className={clsx(
              'flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-medium text-white transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-earth-800',
              isSubmitting
                ? 'bg-lsc-rose/50 cursor-not-allowed'
                : 'bg-lsc-rose hover:bg-lsc-rose/90 focus:ring-lsc-rose'
            )}
            aria-busy={isSubmitting}
          >
            {isSubmitting && <Loader className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />}
            {isSubmitting ? 'Submitting...' : 'Submit Your Question'}
          </button>
        </div>
      </form>

      {/* Response Time Notice */}
      <div className="bg-lsc-cream/50 dark:bg-earth-700/30 rounded-xl p-4 text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <p>
          Our staff typically responds within <strong>2 business days</strong>.
          {branding.phone && (
            <>
              {' '}For urgent questions, call the library at{' '}
              <a
                href={`tel:${branding.phone.replace(/\D/g, '')}`}
                className="text-lsc-rose dark:text-lsc-rose-light hover:underline"
              >
                {branding.phone}
              </a>
              .
            </>
          )}
        </p>
      </div>
    </div>
  )
}