/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Two-Factor Authentication Setup Component
 *
 * Handles the full 2FA lifecycle:
 * - Enable: QR code display + code confirmation
 * - Active: Status display with recovery code count
 * - Disable: Password + TOTP code confirmation
 */
import React, { useState } from 'react'
import toast from 'react-hot-toast'
import {
  Shield,
  ShieldCheck,
  ShieldOff,
  Loader2,
  Copy,
  Check,
  AlertTriangle,
} from 'lucide-react'
import {
  setup2FA,
  confirm2FA,
  disable2FA,
  type TwoFactorSetupResponse,
} from '@/api/account-security-api'
import { useNeurodivergentUX } from '@/hooks/useNeurodivergentUX'
import { useTranslation} from '@/i18n'

interface TwoFactorSetupProps {
  enabled: boolean
  confirmedAt: string | null
  recoveryCodesRemaining: number
  onStatusChange: () => void
}

type SetupStep = 'idle' | 'qr' | 'recovery-codes' | 'disabling'

export const TwoFactorSetup: React.FC<TwoFactorSetupProps> = ({
  enabled,
  confirmedAt,
  recoveryCodesRemaining,
  onStatusChange,
}) => {
  const { simplifiedView, quietMode, focusMode } = useNeurodivergentUX()
  const { t } = useTranslation()
  const twoFALabel = simplifiedView ? 'Extra login security (2FA)' : t('accountSecurity.twoFactor.title')
  const [step, setStep] = useState<SetupStep>('idle')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [setupData, setSetupData] = useState<TwoFactorSetupResponse | null>(null)
  const [code, setCode] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([])
  const [copiedCodes, setCopiedCodes] = useState(false)

  // Disable form state
  const [disablePassword, setDisablePassword] = useState('')
  const [disableCode, setDisableCode] = useState('')

  // Clear sensitive data on unmount
  React.useEffect(() => {
    return () => {
      setSetupData(null)
      setRecoveryCodes([])
      setCode('')
      setDisablePassword('')
      setDisableCode('')
    }
  }, [])

  const handleBeginSetup = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await setup2FA()
      setSetupData(data)
      setStep('qr')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start 2FA setup.')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await confirm2FA(code)
      setSetupData(null)  // Clear TOTP secret immediately
      setRecoveryCodes(data.recovery_codes)
      setStep('recovery-codes')
      onStatusChange()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Invalid code. Try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleDisable = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await disable2FA(disablePassword, disableCode)
      setStep('idle')
      setDisablePassword('')
      setDisableCode('')
      onStatusChange()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to disable 2FA.')
    } finally {
      setLoading(false)
    }
  }

  const handleCopyCodes = async () => {
    try {
      await navigator.clipboard.writeText(recoveryCodes.join('\n'))
      setCopiedCodes(true)
      setTimeout(() => setCopiedCodes(false), 2000)
    } catch {
      toast.error(t('toast.account.couldNotCopyToClipboard'))
    }
  }

  // --- ENABLED STATE ---
  if (enabled && step === 'idle') {
    return (
      <div className="p-6 bg-cream dark:bg-earth-800 rounded-xl">
        <p className="font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          {!focusMode && <ShieldCheck className={`w-5 h-5 ${quietMode ? 'text-lsc-dark/70 dark:text-lsc-cream/70' : 'text-status-success-600 dark:text-status-success-400'}`} />}
          {twoFALabel}
        </p>

        <div className={`p-4 bg-lsc-white dark:bg-lsc-brown rounded-xl border-l-4 ${quietMode ? 'border-earth-400' : 'border-status-success-500'}`}>
          <p className="font-medium text-lsc-dark dark:text-lsc-cream">
            {simplifiedView ? 'Extra login security is active' : t('accountSecurity.twoFactor.active')}
          </p>
          {confirmedAt && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Enabled {new Date(confirmedAt).toLocaleDateString()}
            </p>
          )}

          <div className="mt-3 flex items-center gap-2">
            {recoveryCodesRemaining <= 2 && recoveryCodesRemaining > 0 ? (
              <AlertTriangle className="w-4 h-4 text-status-warning-500" />
            ) : null}
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {simplifiedView ? `${recoveryCodesRemaining} of 8 backup login codes remaining` : t('accountSecurity.twoFactor.recoveryCodesRemaining', { count: recoveryCodesRemaining })}
            </span>
          </div>
          {recoveryCodesRemaining <= 2 && (
            <p className="text-xs text-status-warning-600 dark:text-status-warning-400 mt-1">
              {simplifiedView ? 'Consider regenerating your backup codes below.' : t('accountSecurity.twoFactor.regenerateHint')}
            </p>
          )}
        </div>

        <button
          type="button"
          onClick={() => setStep('disabling')}
          className="mt-4 text-sm text-status-danger-600 dark:text-status-danger-400 hover:underline"
        >
          {simplifiedView ? 'Disable extra login security' : t('accountSecurity.twoFactor.disable')}
        </button>

        {error && (
          <p className="mt-2 text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">{error}</p>
        )}
      </div>
    )
  }

  // --- DISABLE FORM ---
  if (step === 'disabling') {
    return (
      <div className="p-6 bg-cream dark:bg-earth-800 rounded-xl">
        <p className="font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5" />
          {t('accountSecurity.twoFactor.disableTitle')}
        </p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('accountSecurity.twoFactor.disableDesc')}
        </p>
        <form onSubmit={handleDisable} className="space-y-4">
          <div>
            <label htmlFor="2fa-disable-password" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              {t('accountSecurity.twoFactor.password')}
            </label>
            <input
              id="2fa-disable-password"
              type="password"
              autoComplete="current-password"
              value={disablePassword}
              onChange={e => setDisablePassword(e.target.value)}
              className="w-full px-4 py-2 border border-sage/30 dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              required
            />
          </div>
          <div>
            <label htmlFor="2fa-disable-code" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              {t('accountSecurity.twoFactor.authCode')}
            </label>
            <input
              id="2fa-disable-code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={disableCode}
              onChange={e => setDisableCode(e.target.value.replace(/\D/g, ''))}
              className="w-full px-4 py-2 border border-sage/30 dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent font-mono tracking-widest text-center text-lg"
              required
            />
          </div>
          {error && (
            <p className="text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">{error}</p>
          )}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-status-danger-600 text-white rounded-xl hover:bg-status-danger-700 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              {t('accountSecurity.twoFactor.disable2FA')}
            </button>
            <button
              type="button"
              onClick={() => { setStep('idle'); setError('') }}
              className="px-4 py-2 border border-sage/30 dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream hover:bg-sage/10 transition-colors"
            >
              {t('accountSecurity.twoFactor.cancel')}
            </button>
          </div>
        </form>
      </div>
    )
  }

  // --- RECOVERY CODES DISPLAY ---
  if (step === 'recovery-codes') {
    return (
      <div className="p-6 bg-cream dark:bg-earth-800 rounded-xl">
        <p className="font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-status-success-600" />
          {t('accountSecurity.twoFactor.enabled')}
        </p>
        <div className="p-4 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-400 rounded-xl mb-4">
          <p className="font-medium text-status-warning-800 dark:text-status-warning-200">
            {t('accountSecurity.twoFactor.saveRecoveryCodes')}
          </p>
          <p className="text-sm text-status-warning-700 dark:text-status-warning-300 mt-1">
            {t('accountSecurity.twoFactor.saveRecoveryCodesDesc')}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 mb-4">
          {recoveryCodes.map((code, i) => (
            <code
              key={i}
              className="px-3 py-2 bg-lsc-white dark:bg-lsc-brown rounded-lg text-center font-mono text-sm text-lsc-dark dark:text-lsc-cream border border-sage/20 dark:border-earth-600"
            >
              {code}
            </code>
          ))}
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleCopyCodes}
            className="flex items-center gap-2 px-4 py-2 border border-sage/30 dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream hover:bg-sage/10 transition-colors"
          >
            {copiedCodes ? <Check className="w-4 h-4 text-status-success-600" /> : <Copy className="w-4 h-4" />}
            {copiedCodes ? t('accountSecurity.twoFactor.copied') : t('accountSecurity.twoFactor.copy')}
          </button>
        </div>
        <button
          type="button"
          onClick={() => { setStep('idle'); setRecoveryCodes([]) }}
          className="mt-4 w-full bg-lsc-rose text-white py-2 rounded-xl hover:bg-lsc-rose/90 transition-colors"
        >
          {t('accountSecurity.twoFactor.savedCodes')}
        </button>
      </div>
    )
  }

  // --- QR CODE STEP ---
  if (step === 'qr' && setupData) {
    return (
      <div className="p-6 bg-cream dark:bg-earth-800 rounded-xl">
        <p className="font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5" />
          {t('accountSecurity.twoFactor.setupTitle')}
        </p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('accountSecurity.twoFactor.setupDesc')}
        </p>

        <div className="flex justify-center mb-4">
          <div className="p-4 bg-lsc-white rounded-xl">
            <img
              src={setupData.qr_image}
              alt="Scan this QR code with your authenticator app"
              width={200}
              height={200}
            />
          </div>
        </div>

        <details className="mb-4">
          <summary className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer hover:text-lsc-dark dark:hover:text-lsc-cream">
            {t('accountSecurity.twoFactor.cantScan')}
          </summary>
          <code className="block mt-2 p-3 bg-lsc-white dark:bg-lsc-brown rounded-lg text-center font-mono text-sm break-all text-lsc-dark dark:text-lsc-cream">
            {setupData.secret}
          </code>
        </details>

        <form onSubmit={handleConfirm} className="space-y-4">
          <div>
            <label htmlFor="2fa-confirm-code" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              {t('accountSecurity.twoFactor.enterCode')}
            </label>
            <input
              id="2fa-confirm-code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
              className="w-full px-4 py-3 border border-sage/30 dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent font-mono tracking-widest text-center text-xl"
              autoFocus
              required
            />
          </div>
          {error && (
            <p className="text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">{error}</p>
          )}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="flex-1 bg-lsc-rose text-white py-2 rounded-xl hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              {t('accountSecurity.twoFactor.verifyEnable')}
            </button>
            <button
              type="button"
              onClick={() => { setStep('idle'); setSetupData(null); setCode(''); setError('') }}
              className="px-4 py-2 border border-sage/30 dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream hover:bg-sage/10 transition-colors"
            >
              {t('accountSecurity.twoFactor.cancel')}
            </button>
          </div>
        </form>
      </div>
    )
  }

  // --- IDLE / NOT ENABLED ---
  return (
    <div className="p-6 bg-cream dark:bg-earth-800 rounded-xl">
      <p className="font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        {!focusMode && <Shield className="w-5 h-5" />}
        {twoFALabel}
      </p>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        {simplifiedView
          ? 'Add extra security by requiring a code from your phone when you sign in.'
          : t('accountSecurity.twoFactor.description')}
      </p>

      <div className="p-4 bg-lsc-white dark:bg-lsc-brown rounded-xl border border-sage/20 dark:border-earth-700">
        <div className="flex items-start gap-4">
          {!focusMode && (
            <div className={`p-2 rounded-full ${quietMode ? 'bg-lsc-cream dark:bg-earth-800' : 'bg-status-warning-100 dark:bg-status-warning-900/30'}`}>
              <ShieldOff className={`w-6 h-6 ${quietMode ? 'text-lsc-dark/70 dark:text-lsc-cream/70' : 'text-status-warning-600 dark:text-status-warning-400'}`} />
            </div>
          )}
          <div className="flex-1">
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">
              {simplifiedView ? 'Extra login security is not enabled' : t('accountSecurity.twoFactor.notEnabled')}
            </p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {t('accountSecurity.twoFactor.protectAccount')}
            </p>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-sage/20 dark:border-earth-700">
          <button
            type="button"
            onClick={handleBeginSetup}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
            ) : (
              <ShieldCheck className="w-5 h-5" />
            )}
            {simplifiedView ? 'Enable extra login security' : t('accountSecurity.twoFactor.enable')}
          </button>
        </div>
      </div>
      {error && (
        <p className="mt-2 text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">{error}</p>
      )}
    </div>
  )
}
