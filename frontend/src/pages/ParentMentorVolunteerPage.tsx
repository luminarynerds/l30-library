/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Heart, ArrowLeft, CheckCircle, Users } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { FormInput } from '@/components/ui/FormInput'
import { Button } from '@/components/ui/Button'
import { usePageTitle } from '@/hooks/usePageTitle'
import { t } from '@/i18n'

export default function ParentMentorVolunteerPage(): React.ReactElement {
  usePageTitle('Become a Parent Mentor')
  const [submitted, setSubmitted] = useState(false)
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    bio: '',
    availability: [] as string[],
    experience: '',
  })

  const handleChange = (field: string, value: string) => {
    setForm((prev: typeof form) => ({ ...prev, [field]: value }))
  }

  const toggleAvailability = (value: string) => {
    setForm((prev: typeof form) => ({
      ...prev,
      availability: prev.availability.includes(value)
        ? prev.availability.filter((v) => v !== value)
        : [...prev.availability, value],
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
  }

  if (submitted) {
    return (
      <StandardPageLayout
        title="Parent Mentors"
        subtitle="Volunteer as a mentor"
        icon={Heart}
      >
        <div className="max-w-lg mx-auto text-center py-12">
          <div className="w-16 h-16 rounded-full bg-sage-100 dark:bg-sage-900/30 flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-8 h-8 text-sage-600 dark:text-sage-400" aria-hidden="true" />
          </div>
          <h2 className="font-serif text-2xl text-lsc-dark dark:text-lsc-cream mb-3">
            Thank You
          </h2>
          <p className="text-earth-600 dark:text-earth-400 mb-2">
            Your application is in. We&apos;ll reach out within a week with next
            steps, including training details.
          </p>
          <p className="text-sm text-earth-600 dark:text-earth-400 italic mb-8">
            What you&apos;re offering to do matters more than you know.
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
      subtitle="Volunteer as a mentor"
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
            Become a Mentor
          </h2>
          <p className="text-sm text-earth-600 dark:text-earth-400 mb-4">
            You don&apos;t need to be perfect. You just need to remember what it
            felt like.
          </p>

          <div className="p-4 rounded-xl bg-lsc-cream/50 dark:bg-lsc-brown/20 border border-lsc-border dark:border-earth-700/50 space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <p>
              <span className="font-semibold">Stipend:</span> Mentors receive a
              small monthly stipend for their time.
            </p>
            <p>
              <span className="font-semibold">Training:</span> We provide a
              short training session before you start.
            </p>
            <p>
              <span className="font-semibold">Time:</span> As much or as little
              as works for you and your mentee.
            </p>
          </div>
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
              htmlFor="bio"
              className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2"
            >
              Why do you want to be a mentor? <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}> *</span>
            </label>
            <textarea
              id="bio"
              value={form.bio}
              onChange={(e) => handleChange('bio', e.target.value)}
              required
              rows={4}
              placeholder={t('placeholder.parentMentorVolunteer.tellUsABit')}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
            />
          </div>

          <fieldset>
            <legend className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              Availability
            </legend>
            <div className="flex flex-wrap gap-4">
              {[
                { value: 'weekdays', label: 'Weekdays' },
                { value: 'evenings', label: 'Evenings' },
                { value: 'weekends', label: 'Weekends' },
              ].map((option) => (
                <label
                  key={option.value}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={form.availability.includes(option.value)}
                    onChange={() => toggleAvailability(option.value)}
                    className="accent-lsc-rose"
                  />
                  <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {option.label}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <div>
            <label
              htmlFor="experience"
              className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2"
            >
              Any relevant experience?
            </label>
            <textarea
              id="experience"
              value={form.experience}
              onChange={(e) => handleChange('experience', e.target.value)}
              rows={3}
              placeholder={t('placeholder.parentMentorVolunteer.previousMentoringVolunteeringParenting')}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
            />
          </div>

          <div className="pt-4">
            <Button type="submit" leftIcon={<Users className="w-4 h-4" aria-hidden="true" />} loadingAction="submit">
              Submit Application
            </Button>
          </div>
        </form>
      </div>
    </StandardPageLayout>
  )
}
