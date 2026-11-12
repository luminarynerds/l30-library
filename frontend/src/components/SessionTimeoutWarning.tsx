/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import FocusTrap from 'focus-trap-react'
import { Clock, AlertTriangle, X } from 'lucide-react'
import { t } from '@/i18n'

interface SessionTimeoutWarningProps {
  /** Time remaining in seconds */
  timeRemaining: number
  /** Callback when user clicks "Stay Signed In" */
  onExtend: () => void
  /** Callback when user dismisses the warning */
  onDismiss?: () => void
  /** Whether to show the warning */
  show: boolean
}

export default function SessionTimeoutWarning({
  timeRemaining,
  onExtend,
  onDismiss,
  show
}: SessionTimeoutWarningProps): React.ReactElement | null {
  const [secondsLeft, setSecondsLeft] = useState(timeRemaining)

  useEffect(() => {
    setSecondsLeft(timeRemaining)
  }, [timeRemaining])

  useEffect(() => {
    if (!show || secondsLeft <= 0) return

    const interval = setInterval(() => {
      setSecondsLeft(prev => Math.max(0, prev - 1))
    }, 1000)

    return () => clearInterval(interval)
  }, [show, secondsLeft])

  if (!show || secondsLeft <= 0) return null

  const minutes = Math.floor(secondsLeft / 60)
  const seconds = secondsLeft % 60

  const timeDisplay = minutes > 0
    ? `${minutes}:${seconds.toString().padStart(2, '0')}`
    : `${seconds} seconds`

  return (
    <FocusTrap active={show} focusTrapOptions={{ escapeDeactivates: true }}>
    <div
      className="fixed bottom-20 right-4 max-w-md z-50 motion-safe:animate-in motion-safe:slide-in-from-right"
      role="alertdialog"
      aria-labelledby="timeout-warning-title"
      aria-describedby="timeout-warning-description"
      aria-modal="true"
    >
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border-2 border-status-warning-400 dark:border-status-warning-600 overflow-hidden">
        {/* Header */}
        <div className="bg-status-warning-100 dark:bg-status-warning-900/30 px-4 py-3 flex items-center justify-between border-b border-status-warning-200 dark:border-status-warning-800">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400" aria-hidden="true" />
            <h2 id="timeout-warning-title" className="font-serif font-semibold text-status-warning-900 dark:text-status-warning-100">
              Session Expiring Soon
            </h2>
          </div>
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="p-1 hover:bg-status-warning-200 dark:hover:bg-status-warning-800 rounded transition-colors"
              aria-label={t('aria.sessionTimeoutWarning.dismissWarning')}
            >
              <X className="w-4 h-4 text-status-warning-700 dark:text-status-warning-300" aria-hidden="true" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-5">
          {/* Time remaining display */}
          <div className="text-center mb-4">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-xl border border-status-warning-200 dark:border-status-warning-800">
              <AlertTriangle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400" aria-hidden="true" />
              <span className="text-2xl font-bold text-status-warning-700 dark:text-status-warning-300" aria-live="polite">
                {timeDisplay}
              </span>
            </div>
          </div>

          {/* Message */}
          <div id="timeout-warning-description" className="space-y-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
            <p>
              For your security, you'll be automatically signed out if you don't take action.
            </p>
            <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-3">
              <p className="text-earth-900 dark:text-earth-200 font-medium mb-1">
                Don't worry - your work is safe
              </p>
              <p className="text-earth-800 dark:text-lsc-rose-light/80 text-xs">
                Any changes you've made have been automatically saved. You can sign back in anytime to continue.
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-5 flex flex-col gap-2">
            <button
              onClick={onExtend}
              className="w-full px-4 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose flex items-center justify-center gap-2"
              autoFocus
            >
              <Clock className="w-5 h-5" aria-hidden="true" />
              Stay Signed In
            </button>
            <p className="text-xs text-center text-lsc-dark/70 dark:text-lsc-cream/70">
              This will extend your session for another 15 minutes
            </p>
          </div>
        </div>
      </div>
    </div>
    </FocusTrap>
  )
}
