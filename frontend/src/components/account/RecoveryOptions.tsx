/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Recovery Options Component
 *
 * Manages:
 * - Recovery email (set, verify, remove)
 * - Recovery codes count + regenerate
 */
import React, { useState } from 'react'
import { Mail, Key, Loader2, Trash2, Copy } from 'lucide-react'
import toast from 'react-hot-toast'
import { useNeurodivergentUX } from '@/hooks/useNeurodivergentUX'
import { useTranslation} from '@/i18n'
import {
  setRecoveryEmail as setRecoveryEmailApi,
  removeRecoveryEmail,
  regenerateRecoveryCodes,
} from '@/api/account-security-api'
import ConfirmDialog from '../ConfirmDialog'

interface RecoveryOptionsProps {
  totpEnabled: boolean
  recoveryEmailSet: boolean
  recoveryEmailVerified: boolean
  recoveryCodesRemaining: number
  onStatusChange: () => void
}

export const RecoveryOptions: React.FC<RecoveryOptionsProps> = ({
  totpEnabled,
  recoveryEmailSet,
  recoveryEmailVerified,
  recoveryCodesRemaining,
  onStatusChange,
}) => {
  const { simplifiedView } = useNeurodivergentUX()
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Regenerate form
  const [showRegenerate, setShowRegenerate] = useState(false)
  const [regenPassword, setRegenPassword] = useState('')
  const [regenCode, setRegenCode] = useState('')
  const [newCodes, setNewCodes] = useState<string[]>([])

  // Remove confirmation
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false)

  const handleSetEmail = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')
    try {
      const res = await setRecoveryEmailApi(email)
      setSuccess(res.message)
      setEmail('')
      onStatusChange()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to set recovery email.')
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveEmail = async () => {
    setLoading(true)
    setError('')
    try {
      await removeRecoveryEmail()
      onStatusChange()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to remove recovery email.')
    } finally {
      setLoading(false)
    }
  }

  const handleRegenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await regenerateRecoveryCodes(regenPassword, regenCode)
      setNewCodes(res.recovery_codes)
      setRegenPassword('')
      setRegenCode('')
      onStatusChange()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate codes.')
    } finally {
      setLoading(false)
    }
  }

  const handleCopyCodes = async () => {
    try {
      await navigator.clipboard.writeText(newCodes.join('\n'))
      toast.success(t('toast.account.recoveryCodesCopied'))
    } catch {
      toast.error(t('toast.failedToCopy'))
    }
  }

  return (
    <div>
      {/* Recovery Email */}
      <div className="mb-4 p-4 bg-lsc-white dark:bg-lsc-brown rounded-xl">
        <div className="flex items-center gap-2 mb-2">
          <Mail className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{t('accountSecurity.recovery.recoveryEmail')}</span>
        </div>

        {recoveryEmailSet ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
                recoveryEmailVerified
                  ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400'
                  : 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400'
              }`}>
                {recoveryEmailVerified ? t('accountSecurity.recovery.verified') : t('accountSecurity.recovery.pendingVerification')}
              </span>
              {recoveryEmailSet && !recoveryEmailVerified && (
                <button
                  type="button"
                  onClick={() => { if (email) handleSetEmail({ preventDefault: () => {} } as React.FormEvent) }}
                  className="text-xs text-lsc-rose hover:underline"
                >
                  Resend verification
                </button>
              )}
            </div>
            <button
              type="button"
              onClick={() => setShowRemoveConfirm(true)}
              disabled={loading}
              className="text-sm text-status-danger-600 dark:text-status-danger-400 hover:underline flex items-center gap-1"
            >
              <Trash2 className="w-3 h-3" aria-hidden="true" />
              {t('accountSecurity.recovery.remove')}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSetEmail} className="flex gap-2">
            <label htmlFor="recovery-email-input" className="sr-only">Recovery email address</label>
            <input
              id="recovery-email-input"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder={t('placeholder.account.backupexamplecom')}
              className="flex-1 px-3 py-1.5 text-sm border border-sage/30 dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              required
            />
            <button
              type="submit"
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" /> : t('accountSecurity.recovery.add')}
            </button>
          </form>
        )}
      </div>

      {/* Recovery Codes */}
      {totpEnabled && (
        <div className="p-4 bg-lsc-white dark:bg-lsc-brown rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Key className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
              <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{simplifiedView ? 'Backup login codes' : t('accountSecurity.recovery.recoveryCodes')}</span>
            </div>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('accountSecurity.recovery.remaining', { count: recoveryCodesRemaining })}
            </span>
          </div>

          {newCodes.length > 0 ? (
            <div>
              <div className="grid grid-cols-2 gap-1 mb-3">
                {newCodes.map((code, i) => (
                  <code key={i} className="px-2 py-1 text-xs font-mono text-center bg-cream dark:bg-earth-800 rounded text-lsc-dark dark:text-lsc-cream">
                    {code}
                  </code>
                ))}
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleCopyCodes}
                  className="text-xs text-lsc-rose hover:underline flex items-center gap-1"
                >
                  <Copy className="w-3 h-3" aria-hidden="true" />
                  Copy codes
                </button>
                <button
                  type="button"
                  onClick={() => setNewCodes([])}
                  className="text-xs text-lsc-rose hover:underline"
                >
                  {t('accountSecurity.recovery.doneSaved')}
                </button>
              </div>
            </div>
          ) : showRegenerate ? (
            <form onSubmit={handleRegenerate} className="space-y-3 mt-2">
              <div>
                <label htmlFor="regen-password" className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Password</label>
                <input
                  id="regen-password"
                  type="password"
                  autoComplete="current-password"
                  value={regenPassword}
                  onChange={e => setRegenPassword(e.target.value)}
                  className="w-full px-3 py-1.5 text-sm border border-sage/30 dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream"
                  required
                />
              </div>
              <div>
                <label htmlFor="regen-totp-code" className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Authentication code</label>
                <input
                  id="regen-totp-code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  value={regenCode}
                  onChange={e => setRegenCode(e.target.value.replace(/\D/g, ''))}
                  className="w-full px-3 py-1.5 text-sm border border-sage/30 dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream font-mono"
                  required
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="px-3 py-1.5 text-sm bg-lsc-rose text-white rounded-lg disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" /> : t('accountSecurity.recovery.regenerate')}
                </button>
                <button
                  type="button"
                  onClick={() => setShowRegenerate(false)}
                  className="px-3 py-1.5 text-sm border border-sage/30 dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
                >
                  {t('accountSecurity.twoFactor.cancel')}
                </button>
              </div>
            </form>
          ) : (
            <button
              type="button"
              onClick={() => setShowRegenerate(true)}
              className="text-sm text-lsc-rose hover:underline mt-1"
            >
              {t('accountSecurity.recovery.regenerate')}
            </button>
          )}
        </div>
      )}

      {error && <p className="mt-3 text-sm text-status-danger-600 dark:text-status-danger-400" role="alert">{error}</p>}
      {success && <p className="mt-3 text-sm text-status-success-600 dark:text-status-success-400" role="status">{success}</p>}

      <ConfirmDialog
        isOpen={showRemoveConfirm}
        title="Remove Recovery Email"
        message="This will remove your backup recovery email. You won't be able to recover your account via email if you lose access."
        confirmLabel="Remove"
        confirmVariant="danger"
        onConfirm={() => { handleRemoveEmail(); setShowRemoveConfirm(false) }}
        onCancel={() => setShowRemoveConfirm(false)}
      />
    </div>
  )
}
