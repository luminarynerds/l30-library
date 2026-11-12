/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { forgotPassword } from '../api/api'
import { validateEmail } from '../utils/authValidation'
import { normalizeAuthError } from '../utils/authErrors'
import { useTranslation} from '../i18n/I18nContext'
import { TurnstileWidget } from '@/components/TurnstileWidget'

export default function ForgotPasswordPage(): React.ReactElement {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [turnstileToken, setTurnstileToken] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate email before submission
    const emailValidation = validateEmail(email)
    if (!emailValidation.isValid && emailValidation.error) {
      setError(emailValidation.error)
      return
    }

    setIsSubmitting(true)

    try {
      await forgotPassword(email, turnstileToken || undefined)
      setIsSubmitted(true)
    } catch (_err) {
      const authError = normalizeAuthError(_err)
      setError(authError.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isSubmitted) {
    return (
      <main id="main-content" className="min-h-screen flex items-center justify-center bg-lsc-cream dark:bg-lsc-dark px-4">
        <div className="max-w-md w-full bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8 text-center" role="status" aria-live="polite">
          <div className="w-16 h-16 bg-status-success-100 dark:bg-status-success-900 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-status-success-600 dark:text-status-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('auth.checkYourEmail')}</h2>
          <p className="text-lsc-dark/70 dark:text-earth-300 mb-6">
            {t('auth.passwordResetInstructions')}
          </p>
          <Link
            to="/login"
            className="inline-block px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors font-medium" style={{ color: "white" }}
          >
            {t('auth.returnToLogin')}
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main id="main-content" className="min-h-screen flex items-center justify-center bg-lsc-cream dark:bg-lsc-dark px-4">
      <div className="max-w-md w-full bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2 text-center">
          {t('auth.forgotPassword')}
        </h2>
        <p className="text-lsc-dark/70 dark:text-earth-300 mb-6 text-center">
          {t('auth.enterEmailForReset')}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <fieldset className="space-y-4">
          <legend className="sr-only">{t('auth.forgotPassword')}</legend>
          {error && (
            <div
              id="forgot-password-error"
              className="p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-500 rounded-lg text-status-danger-800 dark:text-status-danger-200 text-sm"
              role="alert"
              aria-live="polite"
            >
              {error}
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              {t('auth.emailAddress')} <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              placeholder={t('auth.emailPlaceholder')}
              required
              aria-required="true"
              aria-invalid={!!error}
              aria-describedby={error ? 'forgot-password-error' : undefined}
            />
          </div>
          </fieldset>

          <TurnstileWidget onVerify={setTurnstileToken} />

          <button
            type="submit"
            disabled={isSubmitting || !turnstileToken}
            className="w-full py-2 px-4 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-border disabled:text-lsc-dark/70 !text-white font-medium rounded-lg transition-colors"
          >
            {isSubmitting ? t('auth.sending') : t('auth.sendResetLink')}
          </button>
        </form>

        <p className="mt-6 text-center text-lsc-dark/70 dark:text-earth-300">
          {t('auth.rememberPassword')}{' '}
          <Link to="/login" className="text-lsc-rose hover:text-lsc-rose/90 dark:text-lsc-rose-light font-medium underline decoration-lsc-rose/30 hover:decoration-lsc-rose transition-colors">
            {t('auth.login')}
          </Link>
        </p>
      </div>
    </main>
  )
}
