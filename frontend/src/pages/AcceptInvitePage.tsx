/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef } from "react"
import { Link, useNavigate } from "react-router-dom"
import { acceptInvite } from "@/api/domains/auth/auth-api"
import { validatePassword, validatePasswordMatch } from "../utils/authValidation"
import { normalizeAuthError } from "../utils/authErrors"
import { AUTH_CONFIG } from "../constants/authConfig"
import { useTranslation } from "../i18n/I18nContext"

export default function AcceptInvitePage(): React.ReactElement {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const token = window.location.hash.replace(/^#/, "")

  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [error, setError] = useState("")
  const [passwordError, setPasswordError] = useState(false)
  const [confirmError, setConfirmError] = useState(false)
  const errorRef = useRef<HTMLDivElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (error && errorRef.current) {
      errorRef.current.focus()
    }
  }, [error])

  useEffect(() => {
    if (!token) {
      setError(t("auth.invalidResetLink"))
    }
  }, [token, t])

  useEffect(() => {
    if (isSuccess) {
      const timer = setTimeout(() => {
        navigate("/login")
      }, AUTH_CONFIG.TIMEOUTS.PASSWORD_RESET_SUCCESS)
      return () => clearTimeout(timer)
    }
  }, [isSuccess, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setPasswordError(false)
    setConfirmError(false)

    const passwordValidation = validatePassword(password)
    if (!passwordValidation.isValid && passwordValidation.error) {
      setPasswordError(true)
      setError(passwordValidation.error)
      passwordRef.current?.focus()
      return
    }

    const matchValidation = validatePasswordMatch(password, confirmPassword)
    if (!matchValidation.isValid && matchValidation.error) {
      setConfirmError(true)
      setError(matchValidation.error)
      return
    }

    if (!token) {
      setError(t("auth.invalidResetLink"))
      return
    }

    setIsSubmitting(true)

    try {
      await acceptInvite(token, password)
      setIsSuccess(true)
    } catch (_err) {
      const authError = normalizeAuthError(_err)
      setError(authError.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isSuccess) {
    return (
      <main id="main-content" className="min-h-screen flex items-center justify-center bg-lsc-cream dark:bg-lsc-dark px-4">
        <div className="max-w-md w-full bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-8 text-center">
          <div className="w-16 h-16 bg-status-success-100 dark:bg-status-success-900 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-status-success-600 dark:text-status-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t("auth.passwordResetSuccess")}</h2>
          <p className="text-lsc-dark/70 dark:text-earth-300 mb-6">
            {t("auth.passwordResetSuccessMessage")}
          </p>
          <Link
            to="/login"
            className="inline-block px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors"
          >
            {t("auth.signInNow")}
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main id="main-content" className="min-h-screen flex items-center justify-center bg-lsc-cream dark:bg-lsc-dark px-4">
      <div className="max-w-md w-full bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-8">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2 text-center">
          {t("auth.activateYourAccount")}
        </h2>
        <p className="text-lsc-dark/70 dark:text-earth-300 mb-6 text-center">
          {t("auth.setUpYourAccount")}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <fieldset className="space-y-4">
          <legend className="sr-only">{t("auth.activateYourAccount")}</legend>
          {error && (
            <div
              ref={errorRef}
              id="accept-invite-error"
              tabIndex={-1}
              className="p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-500 rounded-lg text-status-danger-800 dark:text-status-danger-200 text-sm"
              role="alert"
            >
              {error}
            </div>
          )}

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              {t("auth.newPassword")}
            </label>
            <input
              ref={passwordRef}
              id="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); if (passwordError) setPasswordError(false) }}
              className="w-full px-4 py-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              placeholder={t("auth.newPasswordPlaceholder")}
              required
              minLength={8}
              aria-invalid={passwordError}
              aria-describedby={passwordError ? "accept-invite-error password-requirements" : "password-requirements"}
            />
            <p id="password-requirements" className="mt-1.5 text-xs text-lsc-dark/70 dark:text-earth-300">
              {t("auth.passwordRequirements")}
            </p>
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              {t("auth.confirmPassword")}
            </label>
            <input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => { setConfirmPassword(e.target.value); if (confirmError) setConfirmError(false) }}
              className="w-full px-4 py-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              placeholder={t("auth.confirmPasswordPlaceholder")}
              required
              aria-invalid={confirmError}
              aria-describedby={confirmError ? "accept-invite-error" : undefined}
            />
          </div>
          </fieldset>

          <button
            type="submit"
            disabled={isSubmitting || !token}
            className="w-full py-2 px-4 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-border text-white disabled:text-lsc-dark/70 dark:text-lsc-cream/60 font-medium rounded-lg transition-colors"
          >
            {isSubmitting ? t("auth.activating") : t("auth.activateAccount")}
          </button>
        </form>

        <p className="mt-6 text-center text-lsc-dark/70 dark:text-earth-300">
          <Link to="/login" className="text-lsc-rose hover:text-lsc-rose dark:text-lsc-rose-light underline decoration-lsc-rose/30 hover:decoration-lsc-rose transition-colors">
            {t("auth.backToLogin")}
          </Link>
        </p>
      </div>
    </main>
  )
}
