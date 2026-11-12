/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from '@/lib/sentry-lazy'
import { useState } from 'react'
import { fetchApi } from '@/api/fetchApi'
import { AdminShell } from '@/components/shells'

export default function AlternateFormatsRequestPage() {
  const [lesson, setLesson] = useState('')
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (submitting) return
    setError(null)
    setSubmitting(true)
    try {
      await fetchApi('/feature-requests', {
        method: 'POST',
        body: JSON.stringify({
          feature: 'lesson_variant_authoring',
          lesson,
          email,
        }),
      })
      setSubmitted(true)
    } catch (err) {
      Sentry.captureException(err)
      setError("We couldn't record your request. Please try again later.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AdminShell title="Alternate lesson formats">
      <div className="max-w-2xl space-y-6">
        <p className="text-lsc-dark dark:text-lsc-cream">
          Multiple Means of Representation (UDL) -- letting learners pick audio,
          visual, or text versions of a lesson -- is a planned L30 feature. We
          are not building it yet because we want to prioritize based on real
          coordinator demand.
        </p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Tell us which lesson you would use it on first. We will reach out
          when this work is scoped.
        </p>
        {submitted ? (
          <p
            role="status"
            className="rounded-lg border border-green-300 bg-green-50 dark:bg-green-900/20 p-4 text-lsc-dark dark:text-lsc-cream"
          >
            Thanks. We will be in touch when we start scoping this.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              Which lesson would you add an alternate format to first?
              <input
                value={lesson}
                onChange={(e) => setLesson(e.target.value)}
                required
                className="mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 px-3 py-2 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </label>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              Your email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 px-3 py-2 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </label>
            {error && (
              <p role="alert" className="text-sm text-status-danger-500">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 rounded-lg bg-lsc-rose px-6 py-3 font-semibold text-white hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {submitting ? 'Sending...' : 'Send request'}
            </button>
          </form>
        )}
      </div>
    </AdminShell>
  )
}
