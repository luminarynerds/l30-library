/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * ErrorAlert Component
 *
 * Displays inline error messages with brand-friendly messaging and recovery actions.
 * Follows L30 brand voice: warm, helpful, supportive, not blaming.
 *
 * Features:
 * - Multiple error severity levels (error, warning, info)
 * - Recovery action buttons
 * - Error code display for support reference
 * - Accessible with ARIA attributes
 * - Dismissible option
 * - Icons for visual clarity
 *
 * @example
 * ```tsx
 * <ErrorAlert
 *   title="Couldn't save your changes"
 *   message="We're having a temporary issue. Your work is safe."
 *   variant="error"
 *   onRetry={() => saveData()}
 *   errorCode="ERR_500"
 * />
 * ```
 */

import { AlertCircle, AlertTriangle, Info, RefreshCw, X, ExternalLink, LifeBuoy } from 'lucide-react'
import { ReactNode, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useBranding } from '@/contexts/BrandingContext'
import { t } from '@/i18n'
import EscalationModal from '@/components/EscalationModal'

export interface ErrorAlertProps {
  /** Main error title */
  title: string

  /** Detailed error message or description */
  message: string | ReactNode

  /** Error severity/variant */
  variant?: 'error' | 'warning' | 'info'

  /** Show retry button */
  onRetry?: () => void

  /** Retry button text */
  retryText?: string

  /** Show "Go back" or custom action button */
  onAction?: () => void

  /** Action button text */
  actionText?: string

  /** Show contact support affordance. Opens the support ticket modal by default. */
  showSupport?: boolean

  /**
   * Explicit support link (e.g. mailto:). When provided, the contact-support
   * affordance renders as an anchor instead of opening the in-app modal.
   * Leave undefined to use the standard escalation modal flow.
   */
  supportLink?: string

  /** Error code for support reference (shown small and unobtrusive) */
  errorCode?: string

  /** Allow user to dismiss the alert */
  dismissible?: boolean

  /** Callback when dismissed */
  onDismiss?: () => void

  /** Additional CSS classes */
  className?: string
}

export function ErrorAlert({
  title,
  message,
  variant = 'error',
  onRetry,
  retryText = 'Try again',
  onAction,
  actionText = 'Go back',
  showSupport = false,
  supportLink,
  errorCode,
  dismissible = false,
  onDismiss,
  className = '',
}: ErrorAlertProps) {
  const branding = useBranding()
  const location = useLocation()
  const [isDismissed, setIsDismissed] = useState(false)
  const [isSupportOpen, setIsSupportOpen] = useState(false)

  const handleDismiss = () => {
    setIsDismissed(true)
    onDismiss?.()
  }

  // When a supportLink is explicitly passed, preserve legacy anchor behavior.
  // Otherwise the contact-support affordance opens the in-app escalation modal.
  const useModal = showSupport && !supportLink
  const supportHref = supportLink ?? `mailto:${branding.contact_email}`

  // Build a context label for the escalation modal so support staff have a
  // clear pointer back to where the error happened.
  const messageText = typeof message === 'string' ? message : ''
  const supportContext = [
    `Error: ${title}`,
    messageText ? `Details: ${messageText}` : '',
    errorCode ? `Error code: ${errorCode}` : '',
    `Page: ${location.pathname}`,
  ]
    .filter(Boolean)
    .join(' | ')

  if (isDismissed) return null

  const variantStyles = {
    error: {
      container: 'bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-200 dark:border-status-danger-800',
      icon: 'text-status-danger-600 dark:text-status-danger-400',
      title: 'text-status-danger-900 dark:text-status-danger-100',
      message: 'text-status-danger-800 dark:text-status-danger-200',
      code: 'text-status-danger-600/70 dark:text-status-danger-400/70',
      button: 'bg-status-danger-600 hover:bg-status-danger-700 text-white',
      buttonOutline: 'border-status-danger-600 text-status-danger-600 hover:bg-status-danger-600 hover:text-white dark:border-status-danger-400 dark:text-status-danger-400 dark:hover:bg-status-danger-400 dark:hover:text-white',
    },
    warning: {
      container: 'bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800',
      icon: 'text-status-warning-600 dark:text-status-warning-400',
      title: 'text-status-warning-900 dark:text-status-warning-100',
      message: 'text-status-warning-800 dark:text-status-warning-200',
      code: 'text-status-warning-600/70 dark:text-status-warning-400/70',
      button: 'bg-status-warning-600 hover:bg-status-warning-700 text-white',
      buttonOutline: 'border-status-warning-600 text-status-warning-600 hover:bg-status-warning-600 hover:text-white dark:border-status-warning-400 dark:text-status-warning-400 dark:hover:bg-status-warning-400 dark:hover:text-white',
    },
    info: {
      container: 'bg-earth-50 dark:bg-earth-800/20 border-lsc-border dark:border-earth-700',
      icon: 'text-lsc-rose dark:text-lsc-rose-light',
      title: 'text-earth-900 dark:text-earth-200',
      message: 'text-earth-800 dark:text-lsc-rose-light/80',
      code: 'text-lsc-rose dark:text-lsc-rose-light/70 dark:text-lsc-rose-light/70',
      button: 'bg-lsc-rose hover:bg-lsc-rose/90 text-white',
      buttonOutline: 'border-lsc-rose text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-rose hover:text-white dark:border-earth-400 dark:text-lsc-rose-light dark:hover:bg-earth-400 dark:hover:text-white',
    },
  }

  const styles = variantStyles[variant]

  const Icon = variant === 'error' ? AlertCircle : variant === 'warning' ? AlertTriangle : Info

  return (
    <>
    <div
      className={`border rounded-xl p-4 ${styles.container} ${className}`}
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${styles.icon}`} aria-hidden="true" />

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <h3 className={`font-semibold mb-1 ${styles.title}`}>
            {title}
          </h3>

          {/* Message */}
          <div className={`text-sm mb-3 ${styles.message}`}>
            {message}
          </div>

          {/* Error Code (small and unobtrusive) */}
          {errorCode && (
            <div className={`text-xs font-mono mb-3 ${styles.code}`}>
              Error code: {errorCode}
            </div>
          )}

          {/* Action Buttons */}
          {(onRetry || onAction || showSupport) && (
            <div className="flex flex-wrap gap-2 items-center">
              {onRetry && (
                <button
                  onClick={onRetry}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 ${styles.button}`}
                  aria-label={retryText}
                >
                  <RefreshCw className="w-4 h-4" aria-hidden="true" />
                  {retryText}
                </button>
              )}

              {onAction && (
                <button
                  onClick={onAction}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 ${styles.buttonOutline}`}
                  aria-label={actionText}
                >
                  {actionText}
                </button>
              )}

              {showSupport && (
                useModal ? (
                  <button
                    type="button"
                    onClick={() => setIsSupportOpen(true)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 ${styles.buttonOutline}`}
                    aria-label={t('aria.ui.contactSupport')}
                    aria-haspopup="dialog"
                    aria-expanded={isSupportOpen}
                  >
                    Contact support
                    <LifeBuoy className="w-3.5 h-3.5" aria-hidden="true" />
                  </button>
                ) : (
                  <a
                    href={supportHref}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 ${styles.buttonOutline}`}
                    aria-label={t('aria.ui.contactSupport')}
                  >
                    Contact support
                    <ExternalLink className="w-3.5 h-3.5" aria-hidden="true" />
                  </a>
                )
              )}
            </div>
          )}
        </div>

        {/* Dismiss button */}
        {dismissible && (
          <button
            onClick={handleDismiss}
            className={`flex-shrink-0 p-1 rounded-lg transition-colors hover:bg-black/5 dark:hover:bg-lsc-white dark:bg-earth-800/10 ${styles.icon}`}
            aria-label={t('aria.staff.dismissAlert')}
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
    {useModal && (
      <EscalationModal
        isOpen={isSupportOpen}
        onClose={() => setIsSupportOpen(false)}
        hideTrigger
        context={supportContext}
      />
    )}
    </>
  )
}

export function ErrorAlertCompact({
  message,
  variant = 'error',
  dismissible = false,
  onDismiss,
  className = '',
}: Pick<ErrorAlertProps, 'message' | 'variant' | 'dismissible' | 'onDismiss' | 'className'>) {
  const [isDismissed, setIsDismissed] = useState(false)

  const handleDismiss = () => {
    setIsDismissed(true)
    onDismiss?.()
  }

  if (isDismissed) return null

  const variantStyles = {
    error: 'bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-200 dark:border-status-danger-800 text-status-danger-800 dark:text-status-danger-200',
    warning: 'bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800 text-status-warning-800 dark:text-status-warning-200',
    info: 'bg-earth-50 dark:bg-earth-800/20 border-lsc-border dark:border-earth-700 text-earth-800 dark:text-lsc-rose-light/80',
  }

  return (
    <div
      className={`border rounded-lg px-3 py-2 text-sm flex items-center gap-2 ${variantStyles[variant]} ${className}`}
      role="alert"
      aria-live="polite"
    >
      <span className="flex-1">{message}</span>
      {dismissible && (
        <button
          onClick={handleDismiss}
          className="flex-shrink-0 p-0.5 rounded hover:bg-black/5 dark:hover:bg-lsc-white dark:bg-earth-800/10"
          aria-label={t('aria.account.dismiss')}
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}

export default ErrorAlert
