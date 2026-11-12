/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Security Alerts Component
 *
 * Toggle switches for email notification preferences.
 */
import React, { useState } from 'react'
import toast from 'react-hot-toast'
import { updateSecurityAlertPreferences } from '@/api/account-security-api'
import { useNeurodivergentUX } from '@/hooks/useNeurodivergentUX'
import { useTranslation} from '@/i18n'

interface SecurityAlertsProps {
  alertNewLogin: boolean
  alertChanges: boolean
  onStatusChange: () => void
}

export const SecurityAlerts: React.FC<SecurityAlertsProps> = ({
  alertNewLogin,
  alertChanges,
  onStatusChange,
}) => {
  const { simplifiedView } = useNeurodivergentUX()
  const { t } = useTranslation()
  const [newLogin, setNewLogin] = useState(alertNewLogin)
  const [changes, setChanges] = useState(alertChanges)
  const [saving, setSaving] = useState(false)

  const handleToggle = async (field: 'new_login' | 'changes', value: boolean) => {
    const newPrefs = {
      security_alert_new_login: field === 'new_login' ? value : newLogin,
      security_alert_changes: field === 'changes' ? value : changes,
    }

    if (field === 'new_login') setNewLogin(value)
    else setChanges(value)

    setSaving(true)
    try {
      await updateSecurityAlertPreferences(newPrefs)
      onStatusChange()
    } catch {
      // Revert on failure
      if (field === 'new_login') setNewLogin(!value)
      else setChanges(!value)
      toast.error(t('toast.account.failedToUpdateNotificationPreference'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        {simplifiedView ? 'Get notified about important security events.' : t('accountSecurity.alerts.description')}
      </p>

      <div className="space-y-3">
        <div className="flex items-center justify-between p-3 bg-lsc-white dark:bg-lsc-brown rounded-xl">
          <div>
            <p id="alert-new-login-label" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('accountSecurity.alerts.newSignIn')}
            </p>
            <p id="alert-new-login-desc" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('accountSecurity.alerts.newSignInDesc')}
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={newLogin}
            aria-labelledby="alert-new-login-label"
            aria-describedby="alert-new-login-desc"
            onClick={() => handleToggle('new_login', !newLogin)}
            disabled={saving}
            className={`relative w-11 h-6 rounded-full transition-colors ${
              newLogin ? 'bg-lsc-rose' : 'bg-earth-300 dark:bg-earth-600'
            }`}
          >
            <span
              aria-hidden="true"
              className={`absolute top-0.5 left-0.5 w-5 h-5 bg-lsc-white rounded-full transition-transform ${
                newLogin ? 'translate-x-5' : ''
              }`}
            />
          </button>
        </div>

        <div className="flex items-center justify-between p-3 bg-lsc-white dark:bg-lsc-brown rounded-xl">
          <div>
            <p id="alert-changes-label" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('accountSecurity.alerts.securityChange')}
            </p>
            <p id="alert-changes-desc" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('accountSecurity.alerts.securityChangeDesc')}
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={changes}
            aria-labelledby="alert-changes-label"
            aria-describedby="alert-changes-desc"
            onClick={() => handleToggle('changes', !changes)}
            disabled={saving}
            className={`relative w-11 h-6 rounded-full transition-colors ${
              changes ? 'bg-lsc-rose' : 'bg-earth-300 dark:bg-earth-600'
            }`}
          >
            <span
              aria-hidden="true"
              className={`absolute top-0.5 left-0.5 w-5 h-5 bg-lsc-white rounded-full transition-transform ${
                changes ? 'translate-x-5' : ''
              }`}
            />
          </button>
        </div>
      </div>
    </div>
  )
}
