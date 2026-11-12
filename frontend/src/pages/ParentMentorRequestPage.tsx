/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Heart, ArrowLeft, CheckCircle } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { FormInput } from '@/components/ui/FormInput'
import { Button } from '@/components/ui/Button'
import { usePageTitle } from '@/hooks/usePageTitle'
import { t } from '@/i18n'

export default function ParentMentorRequestPage(): React.ReactElement {
  usePageTitle('Find a Parent Mentor')
  const [submitted, setSubmitted] = useState(false)
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    babyAge: '',
    moveTimeline: '',
    needs: '',
    contactMethod: 'text',
  })

  const handleChange = (field: string, value: string) => {
    setForm((prev: typeof form) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
  }

  if (submitted) {
    return (
      <StandardPageLayout
        title="Parent Mentors"
        subtitle="Request a mentor"
        icon={Heart}
      >
        <div className="max-w-lg mx-auto text-center py-12">
          <div className="w-16 h-16 rounded-full bg-sage-100 dark:bg-sage-900/30 flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-8 h-8 text-sage-600 dark:text-sage-400" aria-hidden="true" />
          </div>
          <h2 className="font-serif text-2xl text-lsc-dark dark:text-lsc-cream mb-3">
            We Got You
          </h2>
          <p className="text-earth-600 dark:text-earth-400 mb-2">
            We&apos;ll be in touch within 48 hours to connect you with a mentor
            who gets it.
          </p>
          <p className="text-sm text-earth-600 dark:text-earth-400 italic mb-8">
            You&apos;re not alone. Someone&apos;s going to check on you.
          </p>
          <Link
            to="/parent-mentors"
            className="inline-flex items-center gap-2 text-sm font-medium text-sage-700 dark:text-lsc-rose hover:underline"
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Back to Parent Mentors
          </Link>
        </div>
      </StandardPageLayout>
    )
  }

  return (
    <StandardPageLayout
      title="Parent Mentors"
      subtitle="Request a mentor"
      icon={Heart}
    >
      <div className="max-w-lg mx-auto">
        <Link
          to="/parent-mentors"
          className="inline-flex items-center gap-1.5 text-sm text-sage-700 dark:text-lsc-rose hover:underline mb-6"
        >
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          Back to Parent Mentors
        </Link>

        <div className="mb-8">
          <h2 className="font-serif text-2xl text-lsc-dark dark:text-lsc-cream mb-2">
            I Need a Mentor
          </h2>
          <p className="text-sm text-earth-600 dark:text-earth-400">
            Tell us a little about yourself so we can find the right match. Takes
            about 2 minutes. No judgment, just connection.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <FormInput
            id="name"
            label="Your name"
            isRequired
            value={form.name}
            onChange={(e) => handleChange('name', e.target.value)}
            required
          />

          <FormInput
            id="email"
            label="Email"
            type="email"
            isRequired
            value={form.email}
            onChange={(e) => handleChange('email', e.target.value)}
            required
          />

          <FormInput
            id="phone"
            label="Phone number"
            type="tel"
            value={form.phone}
            onChange={(e) => handleChange('phone', e.target.value)}
          />

          <div>
            <label
              htmlFor="babyAge"
              className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2"
            >
              Baby&apos;s age <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}> *</span>
            </label>
            <select
              id="babyAge"
              value={form.babyAge}
              onChange={(e) => handleChange('babyAge', e.target.value)}
              required
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
            >
              <option value="">Select...</option>
              <option value="expecting">Expecting</option>
              <option value="0-3m">0-3 months</option>
              <option value="3-6m">3-6 months</option>
              <option value="6-12m">6-12 months</option>
              <option value="1-2y">1-2 years</option>
              <option value="2-3y">2-3 years</option>
              <option value="3+">3+ years</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="moveTimeline"
              className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2"
            >
              When did you move here?
            </label>
            <select
              id="moveTimeline"
              value={form.moveTimeline}
              onChange={(e) => handleChange('moveTimeline', e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
            >
              <option value="">Select...</option>
              <option value="less-3m">Less than 3 months ago</option>
              <option value="3-6m">3-6 months ago</option>
              <option value="6-12m">6-12 months ago</option>
              <option value="1-2y">1-2 years ago</option>
              <option value="2+">More than 2 years ago</option>
              <option value="always">I've always lived here</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="needs"
              className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2"
            >
              What do you need most? <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}> *</span>
            </label>
            <textarea
              id="needs"
              value={form.needs}
              onChange={(e) => handleChange('needs', e.target.value)}
              required
              rows={4}
              placeholder={t('placeholder.parentMentorRequest.justSomeoneToTalk')}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
            />
          </div>

          <fieldset>
            <legend className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              Best way to contact you
            </legend>
            <div className="flex flex-wrap gap-4">
              {[
                { value: 'text', label: 'Text' },
                { value: 'email', label: 'Email' },
                { value: 'phone', label: 'Phone call' },
              ].map((option) => (
                <label
                  key={option.value}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <input
                    type="radio"
                    name="contactMethod"
                    value={option.value}
                    checked={form.contactMethod === option.value}
                    onChange={(e) =>
                      handleChange('contactMethod', e.target.value)
                    }
                    className="accent-lsc-rose"
                  />
                  <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {option.label}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="pt-4">
            <Button type="submit" loadingAction="submit">
              Find My Mentor Match
            </Button>
          </div>
        </form>
      </div>
    </StandardPageLayout>
  )
}
