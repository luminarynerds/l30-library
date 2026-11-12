/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { X, Eye, EyeOff, Loader2, CheckCircle, CreditCard, Mail } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { useAuth } from '../contexts/AuthContext'
import { validateEmailLogin, validateCardLogin, validateRegistration } from '../utils/authValidation'
import { normalizeAuthError } from '../utils/authErrors'
import { AUTH_CONFIG, getCardConfig } from '../constants/authConfig'
import ConfirmDialog from './ConfirmDialog'
import { t } from '@/i18n'
import { useBranding } from '../contexts/BrandingContext'
import { TurnstileWidget } from './TurnstileWidget'

interface AuthModalsProps {
  isOpen: boolean
  onClose: () => void
  initialMode?: 'login' | 'register'
}

export default function AuthModals({ isOpen, onClose, initialMode = 'login' }: AuthModalsProps): React.ReactElement | null {
  const [mode, setMode] = useState<'login' | 'register'>(initialMode)
  const [loginMethod, setLoginMethod] = useState<'email' | 'card'>('email')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [libraryCard, setLibraryCard] = useState('')
  const previousActiveElement = useRef<HTMLElement | null>(null)

  const { login, register } = useAuth()
  const branding = useBranding()
  const cardConfig = getCardConfig(branding.card_prefix || AUTH_CONFIG.LIBRARY_CARD.PREFIX)

  // Store the previously focused element and restore on close
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement
    }
  }, [isOpen])

  // Restore focus when modal closes
  const handleClose = useCallback(() => {
    onClose()
    // Restore focus after modal animation completes
    setTimeout(() => {
      if (previousActiveElement.current && typeof previousActiveElement.current.focus === 'function') {
        previousActiveElement.current.focus()
      }
    }, 0)
  }, [onClose])

  const [loginData, setLoginData] = useState({
    email: process.env.NODE_ENV === 'development' ? '' : '',
    password: '',
    card: '',
    pin: '',
  })
  const [turnstileToken, setTurnstileToken] = useState('')

  // Ensure login form is never pre-filled with demo credentials
  useEffect(() => {
    if (isOpen && loginData.email) {
      setLoginData({
        email: '',
        password: '',
        card: '',
        pin: '',
      })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen])

  const [registerData, setRegisterData] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    phone: '',
    address: '',
  })

  const [confirmClose, setConfirmClose] = useState(false)

  if (!isOpen) return null

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate form before submission
    let validationResult
    if (loginMethod === 'email') {
      validationResult = validateEmailLogin(loginData.email, loginData.password)
    } else {
      validationResult = validateCardLogin(loginData.card, loginData.pin, branding.card_prefix)
    }

    if (!validationResult.isValid) {
      const errorValues = Object.values(validationResult.errors)
      setError(errorValues.length > 0 && errorValues[0] ? errorValues[0] : t('auth.genericLoginError', 'We need a bit more information to sign you in'))
      return
    }

    setIsLoading(true)

    try {
      if (loginMethod === 'email') {
        await login(loginData.email, loginData.password, turnstileToken || undefined)
      } else {
        await login(loginData.card, loginData.pin, turnstileToken || undefined)
      }
      setSuccess(true)
      setTimeout(() => {
        handleClose()
        setSuccess(false)
      }, AUTH_CONFIG.TIMEOUTS.MODAL_SUCCESS)
    } catch (_err) {
      const authError = normalizeAuthError(_err)
      setError(authError.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate form before submission
    const validationResult = validateRegistration(registerData)
    if (!validationResult.isValid) {
      const errorValues = Object.values(validationResult.errors)
      setError(errorValues.length > 0 && errorValues[0] ? errorValues[0] : t('auth.genericRegisterError', 'We need a bit more information to create your account'))
      return
    }

    setIsLoading(true)

    try {
      const newUser = await register({ ...registerData, turnstile_token: turnstileToken || undefined })
      setSuccess(true)
      // Get library card from the registered user response
      setLibraryCard(newUser.library_card || '')
      setTimeout(() => {
        handleClose()
        setSuccess(false)
      }, AUTH_CONFIG.TIMEOUTS.MODAL_SUCCESS)
    } catch (_err) {
      const authError = normalizeAuthError(_err)
      setError(authError.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      // Only close if form is empty
      const hasContent = mode === 'login'
        ? loginData.email || loginData.password || loginData.card || loginData.pin
        : Object.values(registerData).some(v => v)

      if (!hasContent) {
        handleClose()
      } else {
        setConfirmClose(true)
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      // Check for unsaved content before closing
      const hasContent = mode === 'login'
        ? loginData.email || loginData.password || loginData.card || loginData.pin
        : Object.values(registerData).some(v => v)

      if (!hasContent) {
        handleClose()
      } else {
        setConfirmClose(true)
      }
    }
  }

  const handleConfirmClose = () => {
    setConfirmClose(false)
    handleClose()
  }

  const handleCancelClose = () => {
    setConfirmClose(false)
  }

  return (
    <FocusTrap
      active={isOpen}
      focusTrapOptions={{
        initialFocus: false,
        allowOutsideClick: false,
        escapeDeactivates: false, // We handle Escape manually
      }}
    >
      <div
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        onClick={handleBackdropClick}
        onKeyDown={handleKeyDown}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
      >
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full max-h-[85vh] sm:max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 flex items-center justify-between p-4 sm:p-6 border-b border-lsc-border dark:border-earth-700 z-10">
          <h2 id="auth-modal-title" className="text-xl sm:text-2xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {success
              ? (mode === 'login' ? t('auth.welcomeBack', 'Welcome Back!') : t('auth.welcome', 'Welcome!'))
              : (mode === 'login' ? t('auth.login', 'Sign In') : t('auth.createYourAccount', 'Create Your Account'))}
          </h2>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors"
            aria-label={t('aria.authModals.close')}
          >
            <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </button>
        </div>

        {/* Success State */}
        {success && (
          <div className="p-8 text-center">
            <CheckCircle className="w-16 h-16 text-status-success-600 mx-auto mb-4" />
            {mode === 'register' && libraryCard && (
              <div className="space-y-3">
                <p className="text-lg text-lsc-dark dark:text-lsc-cream">
                  {t('auth.accountCreatedMessage', 'Your account has been created!')}
                </p>
                <div className="bg-lsc-cream dark:bg-lsc-dark/20 p-4 rounded-lg border-2 border-earth-500">
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                    {t('auth.yourLibraryCardNumber', 'Your Library Card Number:')}
                  </p>
                  <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light font-mono tracking-wider">
                    {libraryCard}
                  </p>
                </div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('auth.signedInStartExploring', "You're now signed in. Start exploring!")}
                </p>
              </div>
            )}
            {mode === 'login' && (
              <p className="text-lg text-lsc-dark dark:text-lsc-cream">
                {t('auth.youreSignedIn', "You're signed in!")}
              </p>
            )}
          </div>
        )}

        {/* Forms */}
        {!success && (
          <div className="p-4 sm:p-6">
            {mode === 'login' ? (
              <form onSubmit={handleLoginSubmit} className="space-y-6">
                {/* Login Method Tabs */}
                <div className="flex gap-2 p-1 bg-lsc-cream dark:bg-lsc-dark rounded-lg" role="tablist" aria-label={t('aria.authModals.loginMethod')}>
                  <button
                    type="button"
                    role="tab"
                    id="login-tab-email"
                    aria-selected={loginMethod === 'email'}
                    aria-controls="login-panel-email"
                    tabIndex={loginMethod === 'email' ? 0 : -1}
                    onClick={() => {
                      setLoginMethod('email')
                      setError('')
                      setLoginData({ email: '', password: '', card: '', pin: '' })
                    }}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-all ${
                      loginMethod === 'email'
                        ? 'bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream shadow-sm'
                        : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
                    }`}
                  >
                    <Mail className="w-4 h-4" aria-hidden="true" />
                    {t('auth.email', 'Email')}
                  </button>
                  <button
                    type="button"
                    role="tab"
                    id="login-tab-card"
                    aria-selected={loginMethod === 'card'}
                    aria-controls="login-panel-card"
                    tabIndex={loginMethod === 'card' ? 0 : -1}
                    onClick={() => {
                      setLoginMethod('card')
                      setError('')
                      setLoginData({ email: '', password: '', card: '', pin: '' })
                    }}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-all ${
                      loginMethod === 'card'
                        ? 'bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream shadow-sm'
                        : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
                    }`}
                  >
                    <CreditCard className="w-4 h-4" aria-hidden="true" />
                    {t('auth.libraryCard', 'Library Card')}
                  </button>
                </div>

                {/* Email Login */}
                {loginMethod === 'email' && (
                  <div id="login-panel-email" role="tabpanel" aria-labelledby="login-tab-email" className="space-y-5">
                    <div>
                      <label htmlFor="login-email" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                        {t('auth.emailAddress', 'Email Address')}
                      </label>
                      <input
                        id="login-email"
                        type="email"
                        autoComplete="email"
                        required
                        autoFocus
                        value={loginData.email}
                        onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                        className="w-full px-4 py-3 text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                        placeholder={t('placeholder.authModals.youremailexamplecom')}
                        maxLength={254}
                      />
                    </div>

                    <div>
                      <label htmlFor="login-password" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                        {t('auth.password', 'Password')}
                      </label>
                      <div className="relative">
                        <input
                          id="login-password"
                          type={showPassword ? 'text' : 'password'}
                          autoComplete="current-password"
                          required
                          value={loginData.password}
                          onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                          className="w-full px-4 py-3 pr-12 text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                          placeholder={t('placeholder.authModals.enterYourPassword')}
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 z-10 p-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose touch-manipulation"
                          aria-label={showPassword ? t('auth.hidePassword', 'Hide password') : t('auth.showPassword', 'Show password')}
                        >
                          {showPassword ? <EyeOff className="w-5 h-5" aria-hidden="true" /> : <Eye className="w-5 h-5" aria-hidden="true" />}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Library Card Login */}
                {loginMethod === 'card' && (
                  <div id="login-panel-card" role="tabpanel" aria-labelledby="login-tab-card" className="space-y-5">
                    <div>
                      <label htmlFor="login-card" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                        {t('auth.libraryCardNumber', 'Library Card Number')}
                      </label>
                      <input
                        id="login-card"
                        type="text"
                        required
                        autoFocus
                        value={loginData.card}
                        onChange={(e) => setLoginData({ ...loginData, card: e.target.value })}
                        className="w-full px-4 py-3 text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream font-mono tracking-wider"
                        placeholder={t('placeholder.authModals.lsc123456', { cardPrefix: cardConfig.PREFIX })}
                      />
                      <p className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {t('auth.cardNumberHelp', { prefix: cardConfig.PREFIX, digits: cardConfig.NUM_DIGITS, example: cardConfig.EXAMPLE })}
                      </p>
                    </div>

                    <div>
                      <label htmlFor="login-pin" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                        {t('auth.pin', 'PIN')}
                      </label>
                      <div className="relative">
                        <input
                          id="login-pin"
                          type={showPassword ? 'text' : 'password'}
                          required
                          value={loginData.pin}
                          onChange={(e) => setLoginData({ ...loginData, pin: e.target.value })}
                          className="w-full px-4 py-3 pr-12 text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                          placeholder={t('placeholder.authModals.enterYourPin')}
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 z-10 p-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose touch-manipulation"
                          aria-label={showPassword ? t('auth.hidePin', 'Hide PIN') : t('auth.showPin', 'Show PIN')}
                        >
                          {showPassword ? <EyeOff className="w-5 h-5" aria-hidden="true" /> : <Eye className="w-5 h-5" aria-hidden="true" />}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Error Message */}
                {error && (
                  <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border-2 border-status-danger-500 rounded-lg" role="alert">
                    <p className="text-sm text-status-danger-800 dark:text-status-danger-200">{error}</p>
                  </div>
                )}

                <TurnstileWidget onVerify={setTurnstileToken} />

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isLoading || !turnstileToken}
                  className="w-full py-4 px-6 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-border font-medium text-lg rounded-lg transition-colors flex items-center justify-center gap-2 focus:ring-4 focus:ring-lsc-border"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 motion-safe:animate-spin text-white" aria-hidden="true" />
                      <span className="text-white">{t('auth.signingIn', 'Signing you in...')}</span>
                    </>
                  ) : (
                    <span className="text-white">{t('auth.loginButton', 'Sign In')}</span>
                  )}
                </button>

                {/* Switch to Register */}
                <div className="text-center pt-4 border-t border-lsc-border dark:border-earth-700">
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('auth.dontHaveAccount', "Don't have an account?")}{' '}
                    <Link
                      to="/register"
                      onClick={onClose}
                      className="text-lsc-rose dark:text-lsc-rose-light font-medium hover:underline focus:underline"
                    >
                      {t('auth.joinWaitingList', 'Join the waiting list')}
                    </Link>
                  </p>
                  <p className="mt-1 text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
                    {t('auth.welcomingInBatches', "We're welcoming new patrons in batches.")}
                  </p>
                </div>

                {/* Forgot Password Link */}
                <div className="text-center">
                  <a href="/forgot-password" className="text-sm text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream hover:underline focus:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-800 rounded">
                    {t('auth.forgotPasswordQuestion', 'Forgot your password?')}
                  </a>
                </div>
              </form>
            ) : (
              // Register Form
              <form onSubmit={handleRegisterSubmit} className="space-y-5">
                <fieldset className="border-0 p-0 m-0">
                  <legend className="text-base font-medium text-lsc-dark dark:text-lsc-cream mb-3">
                    {t('auth.yourName', 'Your Name')}
                  </legend>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="reg-first-name" className="block text-sm font-medium text-lsc-dark/80 dark:text-lsc-cream/80 mb-2">
                        {t('auth.firstName', 'First Name')}
                      </label>
                      <input
                        id="reg-first-name"
                        type="text"
                        autoComplete="given-name"
                        required
                        autoFocus
                        value={registerData.first_name}
                        onChange={(e) => setRegisterData({ ...registerData, first_name: e.target.value })}
                        className="w-full px-4 py-3 text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                        placeholder={t('placeholder.authModals.jane')}
                        maxLength={100}
                      />
                    </div>

                    <div>
                      <label htmlFor="reg-last-name" className="block text-sm font-medium text-lsc-dark/80 dark:text-lsc-cream/80 mb-2">
                        {t('auth.lastName', 'Last Name')}
                      </label>
                      <input
                        id="reg-last-name"
                        type="text"
                        autoComplete="family-name"
                        required
                        value={registerData.last_name}
                        onChange={(e) => setRegisterData({ ...registerData, last_name: e.target.value })}
                        className="w-full px-4 py-3 text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                        placeholder={t('placeholder.addUserModal.doe')}
                        maxLength={100}
                      />
                    </div>
                  </div>
                </fieldset>

                <div>
                  <label htmlFor="reg-email" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                    {t('auth.emailAddress', 'Email Address')}
                  </label>
                  <input
                    id="reg-email"
                    type="email"
                    autoComplete="email"
                    required
                    value={registerData.email}
                    onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                    className="w-full px-4 py-3 text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                    placeholder={t('placeholder.authModals.youremailexamplecom')}
                    maxLength={254}
                  />
                  <p className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('auth.emailHintExtended', 'We use this to send you important updates about your account and items you have on hold.')}
                  </p>
                </div>

                <div>
                  <label htmlFor="reg-password" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                    {t('auth.createPassword', 'Create a Password')}
                  </label>
                  <div className="relative">
                    <input
                      id="reg-password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      required
                      value={registerData.password}
                      onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                      className="w-full px-4 py-3 pr-12 text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                      placeholder={t('placeholder.addUserModal.atLeast8Characters')}
                      minLength={8}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 z-10 p-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose touch-manipulation"
                      aria-label={showPassword ? t('auth.hidePassword', 'Hide password') : t('auth.showPassword', 'Show password')}
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" aria-hidden="true" /> : <Eye className="w-5 h-5" aria-hidden="true" />}
                    </button>
                  </div>
                  <p className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('auth.passwordRequirementsHint', 'Password requirements: at least 8 characters, including an uppercase letter, a lowercase letter, a number, and a special character (like ! @ # $).')}
                  </p>
                </div>

                {/* Optional Fields */}
                <details className="group">
                  <summary className="cursor-pointer text-lsc-rose dark:text-lsc-rose-light font-medium hover:underline list-none">
                    <span className="group-open:hidden">{t('auth.addOptionalFields', '+ Add phone & address (optional)')}</span>
                    <span className="hidden group-open:inline">{t('auth.hideOptionalFields', '- Hide optional fields')}</span>
                  </summary>
                  <div className="mt-4 space-y-4">
                    <div>
                      <label htmlFor="reg-phone" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                        {t('auth.phoneNumber', 'Phone Number')} <span className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">{t('auth.phoneOptionalHint', '(optional - we only use this to text you when your holds are ready)')}</span>
                      </label>
                      <input
                        id="reg-phone"
                        type="tel"
                        autoComplete="tel"
                        value={registerData.phone}
                        onChange={(e) => setRegisterData({ ...registerData, phone: e.target.value })}
                        className="w-full px-4 py-3 text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                        placeholder={t('placeholder.authModals.1234567890')}
                      />
                    </div>

                    <div>
                      <label htmlFor="reg-address" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                        {t('auth.address', 'Address')} <span className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">{t('auth.addressOptionalHint', '(optional - helps us verify you live in our service area)')}</span>
                      </label>
                      <input
                        id="reg-address"
                        type="text"
                        autoComplete="street-address"
                        value={registerData.address}
                        onChange={(e) => setRegisterData({ ...registerData, address: e.target.value })}
                        className="w-full px-4 py-3 text-base border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                        placeholder={t('placeholder.authModals.123MainSt')}
                      />
                    </div>
                  </div>
                </details>

                {/* Error Message */}
                {error && (
                  <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border-2 border-status-danger-500 rounded-lg" role="alert">
                    <p className="text-sm text-status-danger-800 dark:text-status-danger-200">{error}</p>
                  </div>
                )}

                <TurnstileWidget onVerify={setTurnstileToken} />

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isLoading || !turnstileToken}
                  className="w-full py-4 px-6 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-border font-medium text-lg rounded-lg transition-colors flex items-center justify-center gap-2 focus:ring-4 focus:ring-lsc-border"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 motion-safe:animate-spin text-white" aria-hidden="true" />
                      <span className="text-white">{t('auth.creatingAccount', 'Creating your account...')}</span>
                    </>
                  ) : (
                    <span className="text-white">{t('auth.registerButton', 'Create Account')}</span>
                  )}
                </button>

                {/* Switch to Login */}
                <div className="text-center pt-4 border-t border-lsc-border dark:border-earth-700">
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('auth.alreadyHaveAccount', 'Already have an account?')}{' '}
                    <button
                      type="button"
                      onClick={() => {
                        setMode('login')
                        setError('')
                      }}
                      className="text-lsc-rose dark:text-lsc-rose-light font-medium hover:underline focus:underline"
                    >
                      {t('auth.switchToSignIn', 'Sign in')}
                    </button>
                  </p>
                </div>
              </form>
            )}
          </div>
        )}
        </div>

        <ConfirmDialog
          isOpen={confirmClose}
          title={t('auth.leaveWithoutSaving', 'Leave without saving?')}
          message={t('auth.unsavedProgress', "You've started entering some information. Are you sure you want to close? Your progress will be lost.")}
          confirmText={t('auth.leaveAnyway', 'Leave anyway')}
          cancelText={t('auth.stayContinue', 'Stay and continue')}
          confirmVariant="warning"
          onConfirm={handleConfirmClose}
          onCancel={handleCancelClose}
        />
      </div>
    </FocusTrap>
  )
}
