/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { verifyEmail, resendVerification } from '../api/api'
import { useTranslation } from '@/i18n'
import { TurnstileWidget } from '@/components/TurnstileWidget'

export default function VerifyEmailPage(): React.ReactElement {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [isVerifying, setIsVerifying] = useState(true)
  const [isSuccess, setIsSuccess] = useState(false)
  const [error, setError] = useState('')
  const [resendEmail, setResendEmail] = useState('')
  const [isResending, setIsResending] = useState(false)
  const [resendSuccess, setResendSuccess] = useState(false)
  const [resendError, setResendError] = useState('')
  const [turnstileToken, setTurnstileToken] = useState('')

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!resendEmail || isResending || !turnstileToken) return

    setIsResending(true)
    setResendError('')
    setResendSuccess(false)

    try {
      await resendVerification(resendEmail, turnstileToken || undefined)
      setResendSuccess(true)
    } catch {
      // API always returns success for security, but handle network errors
      setResendError('Unable to send email. Please try again.')
    } finally {
      setIsResending(false)
    }
  }

  useEffect(() => {
    const doVerify = async () => {
      if (!token) {
        setError("This verification link isn't working")
        setIsVerifying(false)
        return
      }

      try {
        await verifyEmail(token)
        setIsSuccess(true)
      } catch (_err) {
        setError(_err instanceof Error ? _err.message : 'Verification failed')
      } finally {
        setIsVerifying(false)
      }
    }

    doVerify()
  }, [token])

  if (isVerifying) {
    return (
      <main id="main-content" className="min-h-screen flex items-center justify-center bg-earth-50 dark:bg-earth-900 px-4">
        <div className="max-w-md w-full bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8 text-center">
          <div className="w-16 h-16 border-4 border-lsc-border dark:border-earth-700 border-t-status-warning-600 rounded-full motion-safe:animate-spin mx-auto mb-4"></div>
          <h2 className="text-2xl font-serif font-bold text-earth-800 dark:text-earth-100 mb-2">Verifying...</h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Please wait while we verify your email address.
          </p>
        </div>
      </main>
    )
  }

  if (isSuccess) {
    return (
      <main id="main-content" className="min-h-screen flex items-center justify-center bg-earth-50 dark:bg-earth-900 px-4">
        <div className="max-w-md w-full bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8 text-center">
          <div className="w-16 h-16 bg-status-success-100 dark:bg-status-success-900 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-status-success-600 dark:text-status-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-serif font-bold text-earth-800 dark:text-earth-100 mb-2">Email Verified!</h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
            Your email has been successfully verified. You can now access all features.
          </p>
          <Link
            to="/account"
            className="inline-block px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl transition-colors"
          >
            Go to My Account
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main id="main-content" className="min-h-screen flex items-center justify-center bg-earth-50 dark:bg-earth-900 px-4">
      <div className="max-w-md w-full bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8 text-center">
        <div className="w-16 h-16 bg-status-danger-100 dark:bg-status-danger-900 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-status-danger-600 dark:text-status-danger-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h2 className="text-2xl font-serif font-bold text-earth-800 dark:text-earth-100 mb-2">Verification Failed</h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {error || "The verification link may have expired or isn't working."}
        </p>

        {/* Resend verification section */}
        <div className="bg-earth-100 dark:bg-earth-700 rounded-xl p-4 mb-6">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
            Need a new verification link? Enter your email below.
          </p>
          {resendSuccess ? (
            <div className="text-status-success-600 dark:text-status-success-400 text-sm">
              <p className="font-medium">Verification email sent!</p>
              <p className="text-xs mt-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                Check your inbox (and spam folder) for the new link.
              </p>
            </div>
          ) : (
            <form onSubmit={handleResend} className="space-y-3">
              <input
                type="email"
                value={resendEmail}
                onChange={(e) => setResendEmail(e.target.value)}
                placeholder={t('verifyEmail.enterYourEmailAddress')}
                className="w-full px-4 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-earth-800 dark:text-earth-100 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                required
              />
              {resendError && (
                <p className="text-status-danger-600 dark:text-status-danger-400 text-xs">{resendError}</p>
              )}
              <TurnstileWidget onVerify={setTurnstileToken} />
              <button
                type="submit"
                disabled={isResending || !resendEmail || !turnstileToken}
                className="w-full px-4 py-2 text-sm bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-400 text-white rounded-lg transition-colors"
              >
                {isResending ? 'Sending...' : 'Resend Verification Email'}
              </button>
            </form>
          )}
        </div>

        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Tip: Check your spam or junk folder if you don't see the email.
        </p>

        <Link
          to="/login"
          className="inline-block px-6 py-2 bg-earth-200 hover:bg-earth-300 dark:bg-earth-700 dark:hover:bg-earth-600 text-earth-800 dark:text-earth-100 rounded-xl transition-colors"
        >
          Return to Login
        </Link>
      </div>
    </main>
  )
}
