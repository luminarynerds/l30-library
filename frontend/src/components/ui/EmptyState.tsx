/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * EmptyState Component
 *
 * A reusable component for displaying empty states with the L30 brand voice.
 * This component follows the brand guidelines: warm, helpful, encouraging, and action-oriented.
 *
 * Brand Voice Principles:
 * - Warm & welcoming (not negative or failure-focused)
 * - Helpful & actionable (always suggest next steps)
 * - Encouraging (make empty feel like opportunity, not failure)
 * - Clear & specific (no vague messaging)
 *
 * @see frontend/src/constants/brandMessages.ts
 */

import { type ReactNode, type MouseEventHandler, useMemo } from 'react'
import { type LucideIcon, Lightbulb } from 'lucide-react'
import { clsx } from '@/utils/helpers'


const LIBRARY_TIPS = [
  "Did you know you can request books from other libraries through Interlibrary Loan?",
  "Ask a librarian for reading recommendations tailored to your interests.",
  "Library cards are free for all Creek residents.",
  "Check out our digital collection -- ebooks and audiobooks available 24/7.",
  "Our study rooms can be reserved online up to 2 weeks in advance.",
  "Need help with research? Librarians offer free one-on-one sessions.",
  "We have a Library of Things -- borrow tools, cake pans, and more.",
  "Kids under 5 get their own library card with a parent or guardian.",
]

export interface EmptyStateProps {
  /** Icon to display (lucide-react icon component) */
  icon: LucideIcon
  /** Main heading message */
  title: string
  /** Helpful description or suggestion */
  description: string
  /** Primary action button text (optional) */
  primaryAction?: {
    label: string
    onClick?: MouseEventHandler<HTMLButtonElement>
    href?: string
  }
  /** Secondary action button text (optional) */
  secondaryAction?: {
    label: string
    onClick?: MouseEventHandler<HTMLButtonElement>
    href?: string
  }
  /** Additional help text or tips (optional) */
  helpText?: string
  /** Custom illustration or children to render instead of icon (optional) */
  children?: ReactNode
  /** Size variant */
  size?: 'sm' | 'md' | 'lg'
  /** Visual style variant */
  variant?: 'default' | 'subtle'
  /** Additional CSS classes */
  className?: string
  /** Show a random library tip below the empty state message */
  showTip?: boolean
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  primaryAction,
  secondaryAction,
  helpText,
  children,
  size = 'md',
  className,
  showTip = false,
  variant = 'default',
}: EmptyStateProps): React.ReactElement {
  // Size configurations
  const sizeConfig = {
    sm: {
      container: 'py-8',
      icon: 'w-10 h-10',
      title: 'text-base',
      description: 'text-sm',
      button: 'px-4 py-2 text-sm',
    },
    md: {
      container: 'py-12',
      icon: 'w-12 h-12',
      title: 'text-lg',
      description: 'text-base',
      button: 'px-6 py-2.5 text-base',
    },
    lg: {
      container: 'py-16',
      icon: 'w-16 h-16',
      title: 'text-xl',
      description: 'text-lg',
      button: 'px-8 py-3 text-lg',
    },
  }

  const config = sizeConfig[size]


  const tip = useMemo(() => LIBRARY_TIPS[Math.floor(Math.random() * LIBRARY_TIPS.length)], [])

  // Variant styles
  const iconColor = variant === 'subtle'
    ? 'text-earth-300 dark:text-earth-300'
    : 'text-lsc-rose/30 dark:text-lsc-rose/20'

  return (
    <div
      className={clsx(
        'text-center',
        config.container,
        className
      )}
      role="status"
      aria-live="polite"
    >
      {/* Icon or Custom Children */}
      {children ? (
        <div className="mb-4">{children}</div>
      ) : (
        <Icon
          className={clsx(
            config.icon,
            iconColor,
            'mx-auto mb-4'
          )}
          aria-hidden="true"
        />
      )}

      {/* Title */}
      <h3 className={clsx(
        config.title,
        'font-serif font-medium text-lsc-dark dark:text-lsc-cream mb-2'
      )}>
        {title}
      </h3>

      {/* Description */}
      <p className={clsx(
        config.description,
        'text-lsc-dark/70 dark:text-lsc-cream/70 max-w-md mx-auto'
      )}>
        {description}
      </p>

      {/* Help Text (Optional) */}
      {helpText && (
        <p className={clsx(
          'text-sm text-lsc-dark/70 dark:text-lsc-cream/70 max-w-md mx-auto mt-2'
        )}>
          {helpText}
        </p>
      )}

      {/* Library tip */}
      {showTip && (
        <div className="flex items-center justify-center gap-1.5 max-w-md mx-auto mt-4 pt-3 border-t border-lsc-border/50 dark:border-earth-700/50">
          <Lightbulb className="w-3.5 h-3.5 text-earth-600 dark:text-earth-500 flex-shrink-0" aria-hidden="true" />
          <p className="text-xs text-earth-600 dark:text-earth-500 italic">{tip}</p>
        </div>
      )}

      {/* Actions */}
      {(primaryAction || secondaryAction) && (
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-6">
          {/* Primary Action Button */}
          {primaryAction && (
            <>
              {primaryAction.href ? (
                <a
                  href={primaryAction.href}
                  className={clsx(
                    config.button,
                    'inline-flex items-center justify-center gap-2 min-h-[44px]',
                    'bg-lsc-rose hover:bg-lsc-rose/90 text-white',
                    'rounded-xl font-semibold shadow-sm hover:shadow-md',
                    'transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2',
                    'dark:focus:ring-offset-lsc-dark',
                    'touch-manipulation'
                  )}
                >
                  {primaryAction.label}
                </a>
              ) : (
                <button
                  onClick={primaryAction.onClick}
                  className={clsx(
                    config.button,
                    'inline-flex items-center justify-center gap-2 min-h-[44px]',
                    'bg-lsc-rose hover:bg-lsc-rose/90 text-white',
                    'rounded-xl font-semibold shadow-sm hover:shadow-md',
                    'transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2',
                    'dark:focus:ring-offset-lsc-dark',
                    'touch-manipulation'
                  )}
                >
                  {primaryAction.label}
                </button>
              )}
            </>
          )}

          {/* Secondary Action Button */}
          {secondaryAction && (
            <>
              {secondaryAction.href ? (
                <a
                  href={secondaryAction.href}
                  className={clsx(
                    config.button,
                    'inline-flex items-center justify-center gap-2 min-h-[44px]',
                    'bg-lsc-cream hover:bg-lsc-border dark:bg-lsc-brown dark:hover:bg-lsc-brown/90',
                    'text-lsc-dark dark:text-lsc-cream/80',
                    'border-2 border-lsc-border dark:border-lsc-brown',
                    'rounded-xl font-medium shadow-sm hover:shadow',
                    'transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2',
                    'dark:focus:ring-offset-lsc-dark',
                    'touch-manipulation'
                  )}
                >
                  {secondaryAction.label}
                </a>
              ) : (
                <button
                  onClick={secondaryAction.onClick}
                  className={clsx(
                    config.button,
                    'inline-flex items-center justify-center gap-2 min-h-[44px]',
                    'bg-lsc-cream hover:bg-lsc-border dark:bg-lsc-brown dark:hover:bg-lsc-brown/90',
                    'text-lsc-dark dark:text-lsc-cream/80',
                    'border-2 border-lsc-border dark:border-lsc-brown',
                    'rounded-xl font-medium shadow-sm hover:shadow',
                    'transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2',
                    'dark:focus:ring-offset-lsc-dark',
                    'touch-manipulation'
                  )}
                >
                  {secondaryAction.label}
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

export function EmptyStateCard(props: EmptyStateProps): React.ReactElement {
  return (
    <div className="bg-lsc-cream/50 dark:bg-earth-800/50 rounded-xl border border-lsc-border dark:border-earth-700">
      <EmptyState {...props} />
    </div>
  )
}

export function EmptyStateInline({
  icon: Icon,
  title,
  description,
  primaryAction,
  className,
}: Pick<EmptyStateProps, 'icon' | 'title' | 'description' | 'primaryAction' | 'className'>): React.ReactElement {
  return (
    <div className={clsx('flex items-center gap-4 p-4', className)} role="status" aria-live="polite">
      <Icon className="w-8 h-8 text-lsc-rose/30 dark:text-lsc-rose/20 flex-shrink-0" aria-hidden="true" />
      <div className="flex-1 min-w-0">
        <p className="font-serif font-medium text-lsc-dark dark:text-lsc-cream">{title}</p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{description}</p>
      </div>
      {primaryAction && (
        <>
          {primaryAction.href ? (
            <a
              href={primaryAction.href}
              className="px-4 py-2 min-h-[44px] bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium text-sm shadow-sm hover:shadow-md transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose touch-manipulation flex-shrink-0"
            >
              {primaryAction.label}
            </a>
          ) : (
            <button
              onClick={primaryAction.onClick}
              className="px-4 py-2 min-h-[44px] bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium text-sm shadow-sm hover:shadow-md transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose touch-manipulation flex-shrink-0"
            >
              {primaryAction.label}
            </button>
          )}
        </>
      )}
    </div>
  )
}
