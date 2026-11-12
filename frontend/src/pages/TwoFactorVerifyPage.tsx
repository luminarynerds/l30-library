/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Two-Factor Authentication Verify Page
 *
 * Shown after login when 2FA is required.
 * User enters TOTP code or recovery code to complete sign-in.
 */
import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Shield, Loader2, Key } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { verify2FALogin, verify2FARecovery } from '@/api/account-security-api'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useNeurodivergentUX } from '@/hooks/useNeurodivergentUX'
import { useTranslation} from '@/i18n'
import { TurnstileWidget } from '@/components/TurnstileWidget'

interface LocationState {
  pendingToken?: string
  from?: string
}

export default function TwoFactorVerifyPage(): React.ReactElement {
  const { simplifiedView } = useNeurodivergentUX()
  const { t } = useTranslation()
  usePageTitle(simplifiedView ? 'Extra login security' : t('accountSecurity.verify.title'))
  const navigate = useNavigate()
  const location = useLocation()
  const { completeLogin } = useAuth()

  const state = location.state as LocationState | null
  const pendingToken = state?.pendingToken || ''
  const from = state?.from || '/account'

  const [code, setCode] = useState('')
  const [recoveryCode, setRecoveryCode] = useState('')
  const [showRecovery, setShowRecovery] = useState(false)
  const [trustDevice, setTrustDevice] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [turnstileToken, setTurnstileToken] = useState('')

  // Redirect if no pending token
  if (!pendingToken) {
    navigate('/login', { replace: true })
    return <></> as React.ReactElement
  }

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await verify2FALogin(pendingToken, code, trustDevice, turnstileToken || undefined)
      await completeLogin(response.access_token)
      navigate(from, { replace: true })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Invalid code. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleRecovery = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await verify2FARecovery(pendingToken, recoveryCode, turnstileToken || undefined)
      await completeLogin(response.access_token)
      navigate(from, { replace: true })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Invalid recovery code.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main id="main-content" className="min-h-screen bg-lsc-cream dark:bg-lsc-dark flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20 mb-4">
            <Shield className="w-8 h-8 text-lsc-rose" />
          </div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
            {simplifiedView ? 'Please confirm it\'s you' : t('accountSecurity.verify.title')}
          </h1>
          <p className="text-lsc-dark/70 dark:text-earth-300">
            {simplifiedView
              ? 'Enter the code from your phone app to continue.'
              : t('accountSecurity.verify.subtitle')}
          </p>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8">
          <TurnstileWidget onVerify={setTurnstileToken} />

          {!showRecovery ? (
            <form onSubmit={handleVerify} className="space-y-6">
              <div>
                <label htmlFor="totp-code" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  {t('accountSecurity.verify.authCode')}
                </label>
                <input
                  id="totp-code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  value={code}
                  onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
                  className="w-full px-4 py-3 text-2xl text-center font-mono tracking-[0.5em] border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                  placeholder={t('placeholder.twoFactorVerify.000000')}
                  autoFocus
                  required
                />
              </div>

              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={trustDevice}
                  onChange={e => setTrustDevice(e.target.checked)}
                  className="w-4 h-4 rounded border-sage/30 text-lsc-rose focus:ring-lsc-rose"
                />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('accountSecurity.verify.trustDevice')}
                </span>
              </label>

              {error && (
                <div className="p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-500 rounded-lg" role="alert">
                  <p className="text-sm text-status-danger-800 dark:text-status-danger-200">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || code.length !== 6 || !turnstileToken}
                className="w-full py-3 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-border text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                ) : (
                  t('accountSecurity.verify.verify')
                )}
              </button>

              <button
                type="button"
                onClick={() => { setShowRecovery(true); setError('') }}
                className="w-full text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
              >
                <Key className="w-4 h-4 inline mr-1" />
                {simplifiedView ? 'Use a backup code instead' : t('accountSecurity.verify.useRecovery')}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRecovery} className="space-y-6">
              <div>
                <label htmlFor="recovery-code" className="block text-base font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  {t('accountSecurity.verify.recoveryCode')}
                </label>
                <input
                  id="recovery-code"
                  type="text"
                  value={recoveryCode}
                  onChange={e => setRecoveryCode(e.target.value.toUpperCase())}
                  className="w-full px-4 py-3 text-lg text-center font-mono tracking-wider border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                  placeholder={t('placeholder.twoFactorVerify.xxxxxxxx')}
                  autoFocus
                  required
                />
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-2">
                  {t('accountSecurity.verify.recoveryCodeHint')}
                </p>
              </div>

              {error && (
                <div className="p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-500 rounded-lg" role="alert">
                  <p className="text-sm text-status-danger-800 dark:text-status-danger-200">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || !recoveryCode.trim() || !turnstileToken}
                className="w-full py-3 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-border text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                ) : (
                  t('accountSecurity.verify.useRecoveryCode')
                )}
              </button>

              <button
                type="button"
                onClick={() => { setShowRecovery(false); setError('') }}
                className="w-full text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
              >
                {t('accountSecurity.verify.backToAuth')}
              </button>
            </form>
          )}
        </div>

        <p className="text-center mt-6 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
          <a href="/login" className="text-lsc-rose hover:underline">{t('accountSecurity.verify.backToSignIn')}</a>
        </p>
      </div>
    </main>
  )
}
