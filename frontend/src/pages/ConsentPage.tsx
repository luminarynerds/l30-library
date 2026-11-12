/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  ConsentTokenInfo,
  getParentalConsentInfo,
  submitParentalConsent,
} from '@/api/domains/patron/privacy-api'

type Phase = 'loading' | 'preview' | 'submitting' | 'granted' | 'denied' | 'error'

export default function ConsentPage(): React.ReactElement {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const [phase, setPhase] = useState<Phase>('loading')
  const [info, setInfo] = useState<ConsentTokenInfo | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      setError('This consent link is missing its token. Please use the link from the email exactly.')
      setPhase('error')
      return
    }

    let cancelled = false
    ;(async () => {
      try {
        const data = await getParentalConsentInfo(token)
        if (cancelled) return
        setInfo(data)
        setPhase(data.already_decided ? 'granted' : 'preview')
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'This consent link is no longer valid.')
        setPhase('error')
      }
    })()

    return () => { cancelled = true }
  }, [token])

  const decide = async (consentGiven: boolean) => {
    setPhase('submitting')
    setError('')
    try {
      await submitParentalConsent(token, consentGiven)
      setPhase(consentGiven ? 'granted' : 'denied')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not record your decision.')
      setPhase('error')
    }
  }

  return (
    <main id="main-content" className="min-h-screen flex items-center justify-center bg-earth-50 dark:bg-earth-900 px-4 py-12">
      <div className="max-w-md w-full bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8">
        {phase === 'loading' && (
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-lsc-border dark:border-earth-700 border-t-lsc-rose rounded-full motion-safe:animate-spin mx-auto mb-4" />
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              Loading consent request...
            </h2>
          </div>
        )}

        {phase === 'preview' && info && (
          <div>
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">
              Parental Consent Required
            </h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              A library account has been requested for{' '}
              <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                {info.child_first_name} {info.child_last_initial}.
              </span>
            </p>
            <div className="bg-earth-100 dark:bg-earth-700 rounded-lg p-4 mb-6 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-2">
              <p>
                Under the Children&rsquo;s Online Privacy Protection Act (COPPA),
                a parent or guardian must approve library accounts for children under 13.
              </p>
              <p>
                This request was sent to <span className="font-medium">{info.parent_email}</span>.
                Granting consent activates the account; denying removes it.
              </p>
              <p>
                Your decision and the request details will be recorded in the library&rsquo;s
                consent ledger as required by privacy law.
              </p>
            </div>
            <div className="flex flex-col gap-3">
              <button
                type="button"
                onClick={() => decide(true)}
                className="w-full px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              >
                Grant Consent
              </button>
              <button
                type="button"
                onClick={() => decide(false)}
                className="w-full px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
              >
                Deny &amp; Remove the Account
              </button>
            </div>
          </div>
        )}

        {phase === 'submitting' && (
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-lsc-border dark:border-earth-700 border-t-lsc-rose rounded-full motion-safe:animate-spin mx-auto mb-4" />
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              Recording your decision...
            </h2>
          </div>
        )}

        {phase === 'granted' && (
          <div className="text-center">
            <div className="w-16 h-16 bg-status-success-100 dark:bg-status-success-900 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-status-success-600 dark:text-status-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              Consent Granted
            </h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
              {info ? `${info.child_first_name}'s` : 'The'} library account is now active.
              You can withdraw consent at any time from your account&rsquo;s privacy settings.
            </p>
            <Link
              to="/login"
              className="inline-block px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors"
            >
              Go to Login
            </Link>
          </div>
        )}

        {phase === 'denied' && (
          <div className="text-center">
            <div className="w-16 h-16 bg-earth-100 dark:bg-earth-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-lsc-dark dark:text-lsc-cream" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              Consent Denied
            </h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
              The pending account has been removed. The denial is recorded in our consent ledger.
            </p>
            <Link
              to="/"
              className="inline-block px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors"
            >
              Return Home
            </Link>
          </div>
        )}

        {phase === 'error' && (
          <div className="text-center">
            <div className="w-16 h-16 bg-status-danger-100 dark:bg-status-danger-900 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-status-danger-600 dark:text-status-danger-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              Consent Link Problem
            </h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
              {error || 'This consent link may have expired or already been used.'}
            </p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              The library can resend a fresh consent email if needed.
            </p>
            <Link
              to="/"
              className="inline-block px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors"
            >
              Return Home
            </Link>
          </div>
        )}
      </div>
    </main>
  )
}
