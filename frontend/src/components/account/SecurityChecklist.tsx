/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Security Checklist Banner
 *
 * Calm, encouraging overview of account security status.
 * No scores or pressure colors — just helpful action chips.
 * Hidden in Essentials Mode.
 */
import React from 'react'
import { Shield, Check, ChevronRight } from 'lucide-react'
import type { SecurityOverview } from '@/api/account-security-api'
import { useNeurodivergentUX } from '@/hooks/useNeurodivergentUX'
import { useTranslation } from '@/i18n'

interface SecurityChecklistProps {
  overview: SecurityOverview
  onScrollTo: (section: string) => void
}

export const SecurityChecklist: React.FC<SecurityChecklistProps> = ({
  overview,
  onScrollTo,
}) => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { simplifiedView, quietMode: _quietMode, focusMode: _focusMode } = useNeurodivergentUX()
  const { t } = useTranslation()

  // Hidden in Essentials Mode
  if (simplifiedView) return null

  const items = [
    {
      label: t('accountSecurity.checklist.twoFactor'),
      done: overview.totp_enabled,
      action: t('accountSecurity.checklist.enable2FA'),
      section: '2fa',
    },
    {
      label: t('accountSecurity.checklist.recoveryEmail'),
      done: overview.recovery_email_set && overview.recovery_email_verified,
      action: overview.recovery_email_set ? t('accountSecurity.checklist.verifyEmail') : t('accountSecurity.checklist.addRecoveryEmail'),
      section: 'recovery',
    },
    {
      label: t('accountSecurity.checklist.securityAlerts'),
      done: overview.security_alert_new_login && overview.security_alert_changes,
      action: t('accountSecurity.checklist.reviewAlerts'),
      section: 'alerts',
    },
  ]

  return (
    <div className="p-6 bg-cream dark:bg-earth-800 rounded-xl">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20">
          <Shield className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
        </div>
        <div>
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('accountSecurity.checklist.title')}
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('accountSecurity.checklist.subtitle')}
          </p>
        </div>
      </div>

      <div className="space-y-2">
        {items.map((item) => (
          <div
            key={item.section}
            className="flex items-center justify-between p-3 rounded-lg bg-lsc-white dark:bg-lsc-brown"
          >
            <div className="flex items-center gap-3">
              {item.done ? (
                <div className="w-5 h-5 rounded-full bg-status-success-100 dark:bg-status-success-900/30 flex items-center justify-center">
                  <Check className="w-3.5 h-3.5 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
                </div>
              ) : (
                <div className="w-5 h-5 rounded-full border-2 border-sage/30 dark:border-earth-700" />
              )}
              <span className="sr-only">{item.done ? 'Completed' : 'Not completed'}</span>
              <span id={`checklist-${item.section}-label`} className={`text-sm ${item.done ? 'text-lsc-dark/70 dark:text-lsc-cream/70' : 'text-lsc-dark dark:text-lsc-cream font-medium'}`}>
                {item.label}
              </span>
            </div>
            {!item.done && (
              <button
                type="button"
                aria-describedby={`checklist-${item.section}-label`}
                onClick={() => onScrollTo(item.section)}
                className="flex items-center gap-1 text-xs text-lsc-rose hover:text-lsc-rose/80 font-medium"
              >
                {item.action}
                <ChevronRight className="w-3 h-3" aria-hidden="true" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
