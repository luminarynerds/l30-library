/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { Eye, EyeOff, Loader2, CreditCard, Mail, AlertCircle, Shield, BookOpen } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { browseIndieCatalog } from '@/api/indie-catalog-api'
import { useAuth } from '../contexts/AuthContext'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'
import { requestMagicLink } from '../api/api'
import { validateEmail, validateEmailLogin, validateCardLogin } from '../utils/authValidation'
import { normalizeAuthError } from '../utils/authErrors'
import { useTranslation} from '../i18n/I18nContext'
import { usePageTitle } from '@/hooks/usePageTitle'
import { TurnstileWidget } from '@/components/TurnstileWidget'

interface LocationState {
  from?: string
  holdTitle?: string
  sessionExpired?: boolean
}

export default function LoginPage(): React.ReactElement {
  usePageTitle('Log In')
  const navigate = useNavigate()
  const location = useLocation()
  const { login, isAuthenticated, sessionExpired, clearSessionExpired } = useAuth()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const { t } = useTranslation()

  // Get the intended destination from location state, default to /account
  const locationState = location.state as LocationState | null
  const from = locationState?.from || '/account'
  const holdTitle = locationState?.holdTitle
  const isHoldReturn = from.startsWith('/catalog/') && from.includes('action=hold')

  // Clear session expired flag when component unmounts or user logs in
  useEffect(() => {
    return () => {
      if (sessionExpired) {
        clearSessionExpired()
      }
    }
  }, [sessionExpired, clearSessionExpired])

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, navigate, from])
  const [loginMethod, setLoginMethod] = useState<'email' | 'card' | 'magic'>('email')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [magicLinkSent, setMagicLinkSent] = useState(false)

  const errorRef = useRef<HTMLDivElement>(null)

  // Focus the error summary when errors appear so screen readers announce it
  useEffect(() => {
    if (error && errorRef.current) {
      errorRef.current.focus()
    }
  }, [error])

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    card: '',
    pin: '',
  })
  const [turnstileToken, setTurnstileToken] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMagicLinkSent(false)

    if (loginMethod === 'magic') {
      const emailValidation = validateEmail(formData.email)
      if (!emailValidation.isValid && emailValidation.error) {
        setError(emailValidation.error)
        return
      }

      setIsLoading(true)
      try {
        await requestMagicLink(formData.email, turnstileToken || undefined)
        setMagicLinkSent(true)
      } catch (_err) {
        const authError = normalizeAuthError(_err)
        setError(authError.message)
      } finally {
        setIsLoading(false)
      }
      return
    }

    // Validate form before submission
    let validationResult
    if (loginMethod === 'email') {
      validationResult = validateEmailLogin(formData.email, formData.password)
    } else {
      validationResult = validateCardLogin(formData.card, formData.pin)
    }

    if (!validationResult.isValid) {
      setError(Object.values(validationResult.errors)[0] || t('auth.genericLoginError'))
      return
    }

    setIsLoading(true)

    try {
      let result
      if (loginMethod === 'email') {
        result = await login(formData.email, formData.password, turnstileToken || undefined)
      } else {
        result = await login(formData.card, formData.pin, turnstileToken || undefined)
      }

      // Check if 2FA is required
      if (result && result.requires_2fa) {
        navigate('/2fa-verify', {
          state: { pendingToken: result.pending_token, from },
          replace: true,
        })
        return
      }

      // Clear session expired state and navigate to intended destination
      clearSessionExpired()
      navigate(from, { replace: true })
    } catch (_err) {
      const authError = normalizeAuthError(_err)
      setError(authError.message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main id="main-content" className="min-h-screen bg-lsc-cream dark:bg-lsc-dark flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">
            {t('auth.welcomeBack')}
          </h1>
          <p className="text-lg text-lsc-dark/70 dark:text-earth-300">
            {t('auth.signInToAccount')}
          </p>
        </div>

        {/* Session Expired Banner */}
        {sessionExpired && (
          <div
            className="mb-6 p-4 bg-status-warning-50 dark:bg-status-warning-900/20 border-2 border-status-warning-400 dark:border-status-warning-600 rounded-xl flex items-start gap-3"
            role="alert"
          >
            <AlertCircle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <p className="font-medium text-status-warning-800 dark:text-status-warning-200">
                {t('auth.sessionExpired')}
              </p>
              {from !== '/account' && (
                <p className="text-sm text-status-warning-700 dark:text-status-warning-300 mt-1">
                  {t('auth.returnToPreviousPage')}
                </p>
              )}
            </div>
          </div>
        )}

        {isHoldReturn && (
          <aside
            className="mb-5 flex items-start gap-3 rounded-xl border border-sage-200 bg-sage-50/70 p-4 text-left dark:border-sage-800 dark:bg-sage-900/20"
            aria-label={t('auth.holdContinuation.label', 'Continue your hold')}
          >
            <BookOpen className="mt-0.5 h-5 w-5 flex-shrink-0 text-sage-700 dark:text-lsc-rose" aria-hidden="true" />
            <div>
              <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                {t('auth.holdContinuation.title', 'Continue your hold')}
              </p>
              <p className="mt-1 text-sm leading-relaxed text-earth-700 dark:text-earth-300">
                {holdTitle
                  ? t('auth.holdContinuation.descriptionWithTitle', { title: holdTitle })
                  : t('auth.holdContinuation.description', 'Sign in and we’ll take you back to choose pickup details.')}
              </p>
            </div>
          </aside>
        )}

        {/* Card */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Login Method Tabs */}
            <div className="flex gap-2 p-1 bg-lsc-cream dark:bg-lsc-dark rounded-lg" role="tablist" aria-label={t('auth.loginMethods')}>
              <button
                id="email-tab"
                type="button"
                role="tab"
                aria-selected={loginMethod === 'email'}
                onClick={() => setLoginMethod('email')}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-all ${
                  loginMethod === 'email'
                    ? 'bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream shadow-sm'
                    : 'text-lsc-dark/70 dark:text-earth-300 hover:text-lsc-dark dark:hover:text-lsc-cream'
                }`}
              >
                <Mail className="w-4 h-4" aria-hidden="true" />
                {t('auth.email')}
              </button>
              <button
                id="card-tab"
                type="button"
                role="tab"
                aria-selected={loginMethod === 'card'}
                onClick={() => setLoginMethod('card')}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-all ${
                  loginMethod === 'card'
                    ? 'bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream shadow-sm'
                    : 'text-lsc-dark/70 dark:text-earth-300 hover:text-lsc-dark dark:hover:text-lsc-cream'
                }`}
              >
                <CreditCard className="w-4 h-4" aria-hidden="true" />
                {t('auth.libraryCard')}
              </button>
              <button
                id="magic-tab"
                type="button"
                role="tab"
                aria-selected={loginMethod === 'magic'}
                onClick={() => setLoginMethod('magic')}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-all ${
                  loginMethod === 'magic'
                    ? 'bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream shadow-sm'
                    : 'text-lsc-dark/70 dark:text-earth-300 hover:text-lsc-dark dark:hover:text-lsc-cream'
                }`}
              >
                <Mail className="w-4 h-4" aria-hidden="true" />
                {t('auth.magicLink')}
              </button>
            </div>

            {/* Email Login */}
            {loginMethod === 'email' && (
              <div role="tabpanel" aria-labelledby="email-tab">
              <fieldset className="space-y-5">
                <legend className="sr-only">{t('auth.email')} login credentials</legend>
                <div>
                  <label htmlFor="email" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                    {t('auth.emailAddress')} <span className="text-status-danger-600 dark:text-status-danger-400" aria-label={t('aria.addRoleModal.required')}>*</span>
                  </label>
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    required
                    aria-required="true"
                    aria-invalid={!!error}
                    aria-describedby={error ? 'login-error' : undefined}
                    autoFocus
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-4 py-3 min-h-[44px] text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                    placeholder={t('auth.emailPlaceholder')}
                    maxLength={254}
                  />
                </div>

                <div>
                  <label htmlFor="password" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                    {t('auth.password')} <span className="text-status-danger-600 dark:text-status-danger-400" aria-label={t('aria.addRoleModal.required')}>*</span>
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      required
                      aria-required="true"
                      aria-invalid={!!error}
                      aria-describedby={error ? 'login-error' : undefined}
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      className="w-full px-4 py-3 pr-12 text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                      placeholder={t('auth.enterPassword')}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 z-10 p-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose touch-manipulation"
                      aria-label={showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" aria-hidden="true" /> : <Eye className="w-5 h-5" aria-hidden="true" />}
                    </button>
                  </div>
                </div>
              </fieldset>
              </div>
            )}

            {/* Magic Link */}
            {loginMethod === 'magic' && (
              <div role="tabpanel" aria-labelledby="magic-tab">
              <fieldset className="space-y-3">
                <legend className="sr-only">{t('auth.magicLink')} login</legend>
                <label htmlFor="magic-email" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream">
                  {t('auth.emailAddress')} <span className="text-status-danger-600 dark:text-status-danger-400" aria-label={t('aria.addRoleModal.required')}>*</span>
                </label>
                <input
                  id="magic-email"
                  type="email"
                  autoComplete="email"
                  required
                  aria-required="true"
                  aria-invalid={!!error}
                  aria-describedby={error ? 'login-error' : undefined}
                  autoFocus
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-4 py-3 min-h-[44px] text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                  placeholder={t('auth.emailPlaceholder')}
                  maxLength={254}
                />
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('auth.magicLinkDescription')}
                </p>
                {magicLinkSent && (
                  <p className="text-sm text-status-success-700 dark:text-status-success-400" role="status" aria-live="polite">
                    {t('auth.magicLinkSent')}
                  </p>
                )}
              </fieldset>
              </div>
            )}

            {/* Library Card Login */}
            {loginMethod === 'card' && (
              <div role="tabpanel" aria-labelledby="card-tab">
              <fieldset className="space-y-5">
                <legend className="sr-only">{t('auth.libraryCard')} login credentials</legend>
                <div>
                  <label htmlFor="card" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                    {t('auth.libraryCardNumber')} <span className="text-status-danger-600 dark:text-status-danger-400" aria-label={t('aria.addRoleModal.required')}>*</span>
                  </label>
                  <input
                    id="card"
                    type="text"
                    autoComplete="username"
                    required
                    aria-required="true"
                    aria-invalid={!!error}
                    aria-describedby={error ? 'login-error' : 'card-hint'}
                    autoFocus
                    value={formData.card}
                    onChange={(e) => setFormData({ ...formData, card: e.target.value })}
                    className="w-full px-4 py-3 min-h-[44px] text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream font-mono tracking-wider"
                    placeholder={t('auth.libraryCardPlaceholder')}
                  />
                  <p id="card-hint" className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('auth.libraryCardHint')}
                  </p>
                </div>

                <div>
                  <label htmlFor="pin" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                    {t('auth.pin')} <span className="text-status-danger-600 dark:text-status-danger-400" aria-label={t('aria.addRoleModal.required')}>*</span>
                  </label>
                  <div className="relative">
                    <input
                      id="pin"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      required
                      aria-required="true"
                      aria-invalid={!!error}
                      aria-describedby={error ? 'login-error' : undefined}
                      value={formData.pin}
                      onChange={(e) => setFormData({ ...formData, pin: e.target.value })}
                      className="w-full px-4 py-3 pr-12 text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                      placeholder={t('auth.enterPin')}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 z-10 p-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose touch-manipulation"
                      aria-label={showPassword ? t('auth.hidePin') : t('auth.showPin')}
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" aria-hidden="true" /> : <Eye className="w-5 h-5" aria-hidden="true" />}
                    </button>
                  </div>
                </div>
              </fieldset>
              </div>
            )}

            {/* Error */}
            {error && (
              <div
                ref={errorRef}
                id="login-error"
                tabIndex={-1}
                className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border-2 border-status-danger-500 rounded-lg"
                role="alert"
              >
                <p className="text-sm text-status-danger-800 dark:text-status-danger-200">{error}</p>
              </div>
            )}

            {/* Turnstile widget — required for all login methods, including magic-link */}
            <TurnstileWidget onVerify={setTurnstileToken} />

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading || !turnstileToken}
              className="w-full py-4 px-6 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-border text-white disabled:text-earth-600 font-medium text-lg rounded-lg transition-colors flex items-center justify-center gap-2 focus:ring-4 focus:ring-lsc-border"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                  {loginMethod === 'magic' ? t('auth.sendingLink') : t('auth.signingIn')}
                </>
              ) : (
                loginMethod === 'magic' ? t('auth.sendMagicLink') : t('auth.loginButton')
              )}
            </button>

            {/* Links */}
            <div className="space-y-3 text-center pt-4 border-t border-lsc-border dark:border-earth-700">
              <p className="text-lsc-dark/70 dark:text-earth-300">
                {t('auth.dontHaveAccount')}{' '}
                <Link to="/register" className="text-lsc-rose dark:text-lsc-rose-light font-medium hover:underline">
                  Join the waiting list
                </Link>
              </p>
              <Link to="/forgot-password" className="block text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline focus:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-800 rounded">
                {t('auth.forgotPassword')}
              </Link>
            </div>
          </form>

          {/* Separator */}
        </div>

        {/* Security trust line */}
        <div className="flex items-center justify-center gap-2 mt-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/50">
          <Shield className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
          <p>
            {t('accountSecurity.loginTrustLine')}{' '}
            <Link to="/privacy" className="text-lsc-rose dark:text-lsc-rose-light underline underline-offset-2 focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded">
              {t('accountSecurity.learnMore')}
            </Link>
          </p>
        </div>

        {/* Footer */}
        <p className="text-center mt-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('auth.needHelp')} <Link to="/contact" className="underline underline-offset-2 text-lsc-rose dark:text-lsc-rose-light focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-lsc-dark rounded">{t('auth.contactUs')}</Link>
        </p>

        {/* Indie Ebook Showcase */}
        {isFeatureEnabled('indie_platform_enabled') && <IndieShowcase />}
      </div>
    </main>
  )
}

function IndieShowcase(): React.ReactElement | null {
  const { data } = useQuery({
    queryKey: ['login-indie-showcase'],
    queryFn: () => browseIndieCatalog({ per_page: 6 }),
    staleTime: 300_000,
  })

  if (!data?.items?.length) return null

  return (
    <div className="mt-10 pt-8 border-t border-lsc-border/50 dark:border-earth-700/50">
      <div className="text-center mb-5">
        <div className="flex items-center justify-center gap-2 mb-2">
          <BookOpen className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Indie Author Collection
          </h2>
        </div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
          Borrow local stories for free. Every checkout supports the author.
        </p>
      </div>

      <div className="grid grid-cols-6 gap-2 mb-4">
        {data.items.slice(0, 6).map((ebook) => (
          <div key={ebook.id} className="group relative">
            {ebook.cover_url ? (
              <img
                src={ebook.cover_url}
                alt={ebook.title}
                className="w-full aspect-[2/3] rounded-lg object-cover shadow-sm group-hover:shadow-md transition-shadow"
              />
            ) : (
              <div className="w-full aspect-[2/3] rounded-lg bg-lsc-cream dark:bg-earth-800 flex items-center justify-center">
                <BookOpen className="w-6 h-6 text-lsc-dark/20" />
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="text-center mt-3">
        <Link
          to="/indie"
          className="text-sm text-lsc-rose hover:underline font-medium"
        >
          Browse the collection →
        </Link>
      </div>
    </div>
  )
}
