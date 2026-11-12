/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * ContextualHelp Component
 * In-section help callouts with contextual guidance and action buttons
 * Replaces scattered "Need help?" boxes with accessible, semantic alert containers
 */

import React from 'react'
import { AlertCircle, HelpCircle, CheckCircle, Info, X } from 'lucide-react'
import { clsx } from '../utils/helpers'
import { t } from '@/i18n'

export type ContextualHelpType = 'stuck' | 'info' | 'success' | 'tip'

interface ContextualHelpProps {
  type?: ContextualHelpType
  title: string
  message: string
  actionLabel?: string
  actionUrl?: string
  onAction?: () => void
  onClose?: () => void
  isDismissible?: boolean
  ariaLive?: 'polite' | 'assertive'
}

function getHelpIcon(
  type: ContextualHelpType
): React.ReactNode {
  const iconProps = { className: 'w-5 h-5', 'aria-hidden': true as const }

  switch (type) {
    case 'stuck':
      return <AlertCircle {...iconProps} />
    case 'info':
      return <Info {...iconProps} />
    case 'success':
      return <CheckCircle {...iconProps} />
    case 'tip':
      return <HelpCircle {...iconProps} />
    default:
      return <HelpCircle {...iconProps} />
  }
}

function getHelpStyles(type: ContextualHelpType): {
  container: string
  icon: string
  title: string
  text: string
  button: string
} {
  const styles = {
    stuck: {
      container:
        'bg-status-warning-50 dark:bg-status-warning-900/20 border-l-4 border-status-warning-500 dark:border-status-warning-600',
      icon: 'text-status-warning-600 dark:text-status-warning-500',
      title: 'text-status-warning-900 dark:text-status-warning-100',
      text: 'text-status-warning-800 dark:text-status-warning-200',
      button:
        'bg-status-warning-600 hover:bg-status-warning-700 text-white dark:bg-status-warning-700 dark:hover:bg-status-warning-600',
    },
    info: {
      container:
        'bg-earth-50 dark:bg-earth-800/20 border-l-4 border-lsc-rose/50 dark:border-earth-600',
      icon: 'text-lsc-rose dark:text-lsc-rose-light',
      title: 'text-earth-900 dark:text-earth-200',
      text: 'text-earth-800 dark:text-lsc-rose-light/80',
      button:
        'bg-lsc-rose hover:bg-lsc-rose/90 text-white dark:bg-earth-700 dark:hover:bg-lsc-rose',
    },
    success: {
      container:
        'bg-status-success-50 dark:bg-status-success-900/20 border-l-4 border-status-success-500 dark:border-status-success-600',
      icon: 'text-status-success-600 dark:text-status-success-500',
      title: 'text-status-success-900 dark:text-status-success-100',
      text: 'text-status-success-800 dark:text-status-success-200',
      button:
        'bg-status-success-600 hover:bg-status-success-700 text-white dark:bg-status-success-700 dark:hover:bg-status-success-600',
    },
    tip: {
      container:
        'bg-violet-50 dark:bg-violet-900/20 border-l-4 border-violet-500 dark:border-violet-600',
      icon: 'text-violet-600 dark:text-violet-500',
      title: 'text-violet-900 dark:text-violet-100',
      text: 'text-violet-800 dark:text-violet-200',
      button:
        'bg-violet-600 hover:bg-violet-700 text-white dark:bg-violet-700 dark:hover:bg-violet-600',
    },
  }

  return styles[type] || styles.info
}

function getAriaRole(type: ContextualHelpType): string {
  switch (type) {
    case 'stuck':
      return 'alert'
    case 'success':
      return 'status'
    default:
      return 'region'
  }
}

export function ContextualHelp({
  type = 'info',
  title,
  message,
  actionLabel,
  actionUrl,
  onAction,
  onClose,
  isDismissible = true,
  ariaLive = 'polite',
}: ContextualHelpProps): React.ReactElement {
  const [isDismissed, setIsDismissed] = React.useState(false)

  const handleClose = () => {
    setIsDismissed(true)
    onClose?.()
  }

  if (isDismissed) {
    return <div role="status" className="sr-only">Help message dismissed</div>
  }

  const styles = getHelpStyles(type)
  const icon = getHelpIcon(type)
  const role = getAriaRole(type)

  const handleAction = () => {
    if (actionUrl) {
      window.location.href = actionUrl
    } else if (onAction) {
      onAction()
    }
  }

  return (
    <aside
      className={clsx(
        'rounded-lg p-4 flex gap-4 transition-all duration-200',
        styles.container
      )}
      role={role}
      aria-live={ariaLive}
      aria-label={title}
    >
      {/* Icon container */}
      <div className="flex-shrink-0 pt-0.5">
        <div className={styles.icon}>{icon}</div>
      </div>

      {/* Content container */}
      <div className="flex-1 min-w-0">
        {/* Title */}
        <h3 className={clsx('text-sm font-semibold mb-1', styles.title)}>
          {title}
        </h3>

        {/* Message */}
        <p className={clsx('text-sm mb-3 leading-relaxed', styles.text)}>
          {message}
        </p>

        {/* Action button or link */}
        {(actionLabel || actionUrl || onAction) && (
          <button
            onClick={handleAction}
            className={clsx(
              'inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-transparent focus:ring-current',
              styles.button
            )}
            aria-label={`${actionLabel || 'Get help'} - ${title}`}
          >
            {actionLabel || 'Get Help'}
          </button>
        )}
      </div>

      {/* Close button */}
      {isDismissible && (
        <button
          onClick={handleClose}
          className={clsx(
            'flex-shrink-0 p-1 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-current',
            'hover:bg-black/10 dark:hover:bg-lsc-white dark:bg-earth-800/10'
          )}
          aria-label={t('aria.contextualHelp.dismissHelpMessage')}
          title="Dismiss"
        >
          <X className={clsx('w-4 h-4', styles.icon)} aria-hidden="true" />
        </button>
      )}
    </aside>
  )
}

export default ContextualHelp
