/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { usePageTitle } from '@/hooks/usePageTitle'
import { fetchApi } from '@/api/fetchApi'

// Patron self-serve registration is currently invite-only: new patrons join a
// waiting list instead of creating an account immediately, so the library can
// onboard them in manageable batches. Existing patrons still sign in at /login.
export default function RegisterPage() {
  usePageTitle('Join the waiting list')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await fetchApi('/waitlist', {
        method: 'POST',
        body: JSON.stringify({ email, source: 'register' }),
      })
      setSubmitted(true)
    } catch (err) {
      const message = (err as { message?: string })?.message
      setError(message || 'Unable to join the list right now. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main id="main-content" className="min-h-screen bg-lsc-cream dark:bg-lsc-dark flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">Join the waiting list</h1>
          <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">
            We're welcoming new patrons in batches. Add your email and we'll invite you to set up your library account.
          </p>
        </div>

        <div className="bg-white dark:bg-earth-800 rounded-xl shadow-lg p-8">
          {submitted ? (
            <div role="status" aria-live="polite" className="text-center space-y-3">
              <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">You're on the list.</h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Thanks for your interest. We'll email <strong>{email}</strong> when it's your turn to set up an account.
              </p>
              <Link to="/" className="inline-block text-lsc-rose dark:text-lsc-rose-light font-medium hover:underline">
                Back to home
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              {error && (
                <div role="alert" className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-300">
                  {error}
                </div>
              )}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full px-3 py-2 rounded-lg border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 disabled:opacity-70 text-white font-medium rounded-xl transition-colors"
              >
                {loading ? 'Joining…' : 'Join the waiting list'}
              </button>
            </form>
          )}

          <p className="mt-6 text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Already have an account?{' '}
            <Link to="/login" className="text-lsc-rose dark:text-lsc-rose-light font-medium hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </main>
  )
}
