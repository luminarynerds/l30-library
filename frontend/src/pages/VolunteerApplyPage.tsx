/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Heart, ArrowLeft, CheckCircle, Users } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { FormInput } from '@/components/ui/FormInput'
import { Button } from '@/components/ui/Button'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useAuth } from '@/contexts/AuthContext'
import { volunteerApi, type VolunteerApplication } from '@/api/domains/admin/volunteer-api'

const INTEREST_OPTIONS = [
  'Shelving & Sorting',
  'Event Support',
  'Storytime Helper',
  'Reading Buddy',
  'Tech Help',
  'Outreach & Delivery',
  'Garden & Grounds',
  'Translation',
  'Special Projects',
]

const AVAILABILITY_OPTIONS = ['Weekday mornings', 'Weekday afternoons', 'Evenings', 'Weekends']

interface FormState {
  first_name: string
  last_name: string
  email: string
  phone: string
  address: string
  interests: string[]
  skills: string
  why_volunteer: string
  availability: string[]
  background_check_consent: boolean
}

export default function VolunteerApplyPage(): React.ReactElement {
  usePageTitle('Apply to Volunteer')
  const navigate = useNavigate()
  const { user } = useAuth()

  const [attempted, setAttempted] = useState(false)
  const [form, setForm] = useState<FormState>(() => ({
    first_name: user?.first_name ?? '',
    last_name: user?.last_name ?? '',
    email: user?.email ?? '',
    phone: '',
    address: '',
    interests: [],
    skills: '',
    why_volunteer: '',
    availability: [],
    background_check_consent: false,
  }))

  const errors = useMemo(() => {
    const e: Partial<Record<keyof FormState, string>> = {}
    if (!form.first_name.trim()) e.first_name = 'First name is required'
    if (!form.last_name.trim()) e.last_name = 'Last name is required'
    if (!form.email.trim()) e.email = 'Email is required'
    if (!form.phone.trim()) e.phone = 'Phone number is required'
    if (form.interests.length === 0) e.interests = 'Pick at least one area of interest'
    if (!form.why_volunteer.trim()) e.why_volunteer = 'Please tell us why you want to volunteer'
    if (!form.background_check_consent) e.background_check_consent = 'Background check consent is required'
    return e
  }, [form])

  const isValid = Object.keys(errors).length === 0

  const submit = useMutation({
    mutationFn: async (payload: VolunteerApplication) => {
      const draft = await volunteerApi.submitApplication(payload) as { id: number }
      await volunteerApi.submitApplicationForReview(draft.id)
      return draft
    },
    onSuccess: () => {
      toast.success('Application submitted. Library staff will follow up shortly.')
      navigate('/account?tab=volunteer')
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : 'Could not submit application'
      toast.error(message)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setAttempted(true)
    if (!isValid || submit.isPending) return
    const payload: VolunteerApplication = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      email: form.email.trim(),
      phone: form.phone.trim(),
      address: form.address.trim() || undefined,
      interests: form.interests,
      skills: form.skills
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      why_volunteer: form.why_volunteer.trim(),
      background_check_consent: form.background_check_consent,
      availability: form.availability.join('; ') || undefined,
    }
    submit.mutate(payload)
  }

  const toggle = (list: 'interests' | 'availability', value: string) => {
    setForm((prev) => ({
      ...prev,
      [list]: prev[list].includes(value)
        ? prev[list].filter((v) => v !== value)
        : [...prev[list], value],
    }))
  }

  if (submit.isSuccess) {
    return (
      <StandardPageLayout title="Volunteer" subtitle="Application received" icon={Heart}>
        <div className="max-w-lg mx-auto text-center py-12">
          <div className="w-16 h-16 rounded-full bg-sage-100 dark:bg-sage-900/30 flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-8 h-8 text-sage-600 dark:text-sage-400" aria-hidden="true" />
          </div>
          <h2 className="font-serif text-2xl text-lsc-dark dark:text-lsc-cream mb-3">Thank you</h2>
          <p className="text-earth-600 dark:text-earth-400 mb-8">
            Your application is in. A staff member will follow up about next steps and a brief
            interview.
          </p>
          <Link
            to="/account?tab=volunteer"
            className="inline-flex items-center gap-2 text-sm font-medium text-sage-700 dark:text-lsc-rose hover:underline"
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Back to your account
          </Link>
        </div>
      </StandardPageLayout>
    )
  }

  return (
    <StandardPageLayout title="Volunteer" subtitle="Apply to volunteer" icon={Heart}>
      <div className="max-w-2xl mx-auto">
        <Link
          to="/account?tab=volunteer"
          className="inline-flex items-center gap-1.5 text-sm text-sage-700 dark:text-lsc-rose hover:underline mb-6"
        >
          <ArrowLeft className="w-4 h-4" aria-hidden="true" />
          Back to your account
        </Link>

        <div className="mb-8">
          <h2 className="font-serif text-2xl text-lsc-dark dark:text-lsc-cream mb-2">
            Volunteer with the library
          </h2>
          <p className="text-sm text-earth-600 dark:text-earth-400">
            Tell us a little about yourself. We&apos;ll review your application and reach out about
            next steps, including any required orientation.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormInput
              id="first_name"
              label="First name"
              isRequired
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              error={attempted ? errors.first_name : undefined}
              autoComplete="given-name"
              required
            />
            <FormInput
              id="last_name"
              label="Last name"
              isRequired
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              error={attempted ? errors.last_name : undefined}
              autoComplete="family-name"
              required
            />
          </div>

          <FormInput
            id="email"
            label="Email"
            type="email"
            isRequired
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            error={attempted ? errors.email : undefined}
            autoComplete="email"
            required
          />

          <FormInput
            id="phone"
            label="Phone number"
            type="tel"
            isRequired
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
            error={attempted ? errors.phone : undefined}
            autoComplete="tel"
            required
          />

          <FormInput
            id="address"
            label="Address (optional)"
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
            autoComplete="street-address"
          />

          <fieldset>
            <legend className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              Areas of interest <span className="text-status-danger-600" aria-hidden="true"> *</span>
              <span className="sr-only"> (required, pick at least one)</span>
            </legend>
            <div className="flex flex-wrap gap-2">
              {INTEREST_OPTIONS.map((opt) => {
                const checked = form.interests.includes(opt)
                return (
                  <label
                    key={opt}
                    className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm cursor-pointer transition-colors ${
                      checked
                        ? 'bg-sage-100 dark:bg-sage-900/30 border-sage-500 text-sage-800 dark:text-sage-100'
                        : 'bg-lsc-white dark:bg-earth-700 border-lsc-border dark:border-earth-700 text-earth-700 dark:text-lsc-cream'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle('interests', opt)}
                      className="sr-only"
                    />
                    {opt}
                  </label>
                )
              })}
            </div>
            {attempted && errors.interests && (
              <p className="mt-2 text-sm text-status-danger-600">{errors.interests}</p>
            )}
          </fieldset>

          <div>
            <label
              htmlFor="why_volunteer"
              className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2"
            >
              Why do you want to volunteer? <span className="text-status-danger-600" aria-hidden="true"> *</span>
            </label>
            <textarea
              id="why_volunteer"
              value={form.why_volunteer}
              onChange={(e) => setForm({ ...form, why_volunteer: e.target.value })}
              required
              rows={4}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
              aria-invalid={Boolean(attempted && errors.why_volunteer)}
            />
            {attempted && errors.why_volunteer && (
              <p className="mt-1 text-sm text-status-danger-600">{errors.why_volunteer}</p>
            )}
          </div>

          <fieldset>
            <legend className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              When are you usually available?
            </legend>
            <div className="flex flex-wrap gap-4">
              {AVAILABILITY_OPTIONS.map((opt) => (
                <label key={opt} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.availability.includes(opt)}
                    onChange={() => toggle('availability', opt)}
                    className="accent-lsc-rose"
                  />
                  <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{opt}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div>
            <label
              htmlFor="skills"
              className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2"
            >
              Relevant skills (optional)
            </label>
            <input
              id="skills"
              type="text"
              value={form.skills}
              onChange={(e) => setForm({ ...form, skills: e.target.value })}
              placeholder="e.g. teaching, Spanish, light carpentry"
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
            />
            <p className="mt-1 text-xs text-earth-600 dark:text-earth-400">
              Separate multiple skills with commas.
            </p>
          </div>

          <label className="flex items-start gap-3 p-4 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-lsc-brown/20 cursor-pointer">
            <input
              type="checkbox"
              checked={form.background_check_consent}
              onChange={(e) =>
                setForm({ ...form, background_check_consent: e.target.checked })
              }
              className="mt-1 accent-lsc-rose"
              aria-describedby="bgcheck-help"
              required
            />
            <span className="text-sm text-lsc-dark dark:text-lsc-cream">
              I consent to a background check if my role requires one.{' '}
              <span className="text-status-danger-600" aria-hidden="true">*</span>
              <span id="bgcheck-help" className="block text-xs text-earth-600 dark:text-earth-400 mt-1">
                Some volunteer roles, especially those working with youth, require a background
                check before you can start.
              </span>
            </span>
          </label>
          {attempted && errors.background_check_consent && (
            <p className="text-sm text-status-danger-600">{errors.background_check_consent}</p>
          )}

          <div className="pt-2">
            <Button
              type="submit"
              leftIcon={<Users className="w-4 h-4" aria-hidden="true" />}
              isLoading={submit.isPending}
              loadingAction="submit"
              disabled={submit.isPending}
            >
              Submit application
            </Button>
          </div>
        </form>
      </div>
    </StandardPageLayout>
  )
}
