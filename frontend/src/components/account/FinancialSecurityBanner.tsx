/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Financial Security Banner
 *
 * Soft, encouraging nudge for users with financial data linked (Stripe Connect)
 * to enable two-factor authentication. Dismissable with 30-day reappearance.
 *
 * - Only shown when has_stripe_connected is true and 2FA is not enabled
 * - Respects neurodivergent settings (quietMode, simplifiedView)
 * - Stores dismissal timestamp in localStorage; reappears after 30 days
 */
import React, { useState, useEffect } from 'react'
import { Shield, X } from 'lucide-react'
import { useNeurodivergentUX } from '@/hooks/useNeurodivergentUX'
import { t } from '@/i18n'

const DISMISSAL_KEY = 'l30_financial_2fa_banner_dismissed_at'
const REAPPEAR_DAYS = 30
const REAPPEAR_MS = REAPPEAR_DAYS * 24 * 60 * 60 * 1000

interface FinancialSecurityBannerProps {
  hasStripeConnected: boolean
  totpEnabled: boolean
  onScrollTo2FA: () => void
}

export const FinancialSecurityBanner: React.FC<FinancialSecurityBannerProps> = ({
  hasStripeConnected,
  totpEnabled,
  onScrollTo2FA,
}) => {
  const { simplifiedView, quietMode } = useNeurodivergentUX()
  const [dismissed, setDismissed] = useState(true) // Start hidden to avoid flash

  useEffect(() => {
    // Check localStorage for prior dismissal
    const storedTimestamp = localStorage.getItem(DISMISSAL_KEY)
    if (!storedTimestamp) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reads localStorage once on mount with a conditional removeItem WRITE; real side-effect, not derived state
      setDismissed(false)
      return
    }

    const dismissedAt = parseInt(storedTimestamp, 10)
    if (isNaN(dismissedAt)) {
      setDismissed(false)
      return
    }

    const elapsed = Date.now() - dismissedAt
    if (elapsed >= REAPPEAR_MS) {
      // Enough time has passed, show again
      localStorage.removeItem(DISMISSAL_KEY)
      setDismissed(false)
    } else {
      setDismissed(true)
    }
  }, [])

  const handleDismiss = () => {
    localStorage.setItem(DISMISSAL_KEY, Date.now().toString())
    setDismissed(true)
  }

  // Don't render if conditions aren't met
  if (!hasStripeConnected || totpEnabled || dismissed) return null

  // In simplified view, show a minimal single-line version
  if (simplifiedView) {
    return (
      <div
        role="status"
        className="p-4 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400 shrink-0" />
          <span className="text-sm text-status-warning-800 dark:text-status-warning-200">
            Financial data linked. Consider enabling 2FA.
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={onScrollTo2FA}
            className="text-xs font-medium text-status-warning-700 dark:text-status-warning-300 hover:underline"
          >
            Set up
          </button>
          <button
            type="button"
            onClick={handleDismiss}
            aria-label={t('aria.account.dismiss')}
            className="p-1 text-status-warning-500 dark:text-status-warning-400 hover:text-status-warning-700 dark:hover:text-status-warning-200"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      role="status"
      className="p-5 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-full bg-status-warning-100 dark:bg-status-warning-900/40 shrink-0 mt-0.5">
            <Shield className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400" />
          </div>
          <div>
            <h4 className="font-medium text-status-warning-900 dark:text-status-warning-100 mb-1">
              {quietMode
                ? 'Two-factor authentication recommended'
                : 'Protect your financial data with two-factor authentication'}
            </h4>
            <p className="text-sm text-status-warning-700 dark:text-status-warning-300 leading-relaxed">
              {quietMode
                ? 'Your account has financial data linked. Adding 2FA provides an extra layer of protection.'
                : 'Your account has financial data linked through Stripe Connect. We recommend enabling two-factor authentication to add an extra layer of security to your account.'}
            </p>
            <button
              type="button"
              onClick={onScrollTo2FA}
              className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-status-warning-700 dark:text-status-warning-300 hover:text-status-warning-900 dark:hover:text-status-warning-100 transition-colors"
            >
              <Shield className="w-4 h-4" />
              Set up two-factor authentication
            </button>
          </div>
        </div>
        <button
          type="button"
          onClick={handleDismiss}
          aria-label={t('aria.account.dismissFinancialSecurityRecommendation')}
          className="p-1.5 text-status-warning-400 dark:text-status-warning-500 hover:text-status-warning-600 dark:hover:text-status-warning-300 rounded-lg hover:bg-status-warning-100 dark:hover:bg-status-warning-900/40 transition-colors shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
