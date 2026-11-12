/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * LoadingSpinner Component
 *
 * A reusable loading spinner that respects reduced motion preferences.
 * Uses Tailwind's motion-reduce and motion-safe variants to automatically
 * adapt to user preferences (both from accessibility settings and system
 * prefers-reduced-motion media query).
 *
 * Features branded, friendly loading messages that reflect the library's
 * warm, community-focused voice.
 *
 * @example
 * // Basic usage
 * <LoadingSpinner />
 *
 * // With custom size
 * <LoadingSpinner size="lg" />
 *
 * // With label (recommended for accessibility)
 * <LoadingSpinner label="Loading content..." />
 */

import { Loader2 } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { getRandomLoadingMessageKey, getPageLoadingMessageKey } from '@/constants/brandMessages'
import { useTranslation } from '@/i18n/I18nContext'

interface LoadingSpinnerProps {
  /** Size variant of the spinner */
  size?: 'sm' | 'md' | 'lg' | 'xl'
  /** Custom className for additional styling */
  className?: string
  /** Accessible label for screen readers (defaults to a friendly branded message) */
  label?: string
  /** Color class for the spinner */
  color?: string
  /** Whether to show the label text visibly (not just for screen readers) */
  showLabel?: boolean
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-12 h-12',
}

export default function LoadingSpinner({
  size = 'md',
  className,
  label,
  color = 'text-lsc-rose',
  showLabel = false,
}: LoadingSpinnerProps): React.ReactElement {
  const { t } = useTranslation()
  // Use a friendly branded message if no custom label provided
  const displayLabel = label ?? t(getRandomLoadingMessageKey())

  return (
    <span role="status" aria-label={displayLabel} className="inline-flex items-center gap-2">
      <Loader2
        aria-hidden="true"
        className={clsx(
          sizeClasses[size],
          color,
          // Only animate when motion is safe (not reduced)
          'motion-safe:animate-spin',
          // When motion is reduced, show a subtle pulse instead (or static)
          'motion-reduce:animate-none',
          className
        )}
      />
      {showLabel ? (
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{displayLabel}</span>
      ) : (
        <span className="sr-only">{displayLabel}</span>
      )}
    </span>
  )
}

export function PageLoadingSpinner({
  label,
  page,
}: {
  /** Custom label (overrides page-specific default) */
  label?: string
  /** Page context for branded loading message */
  page?: 'catalog' | 'events' | 'notifications' | 'account'
}): React.ReactElement {
  const { t } = useTranslation()
  // Use page-specific message if page is provided, otherwise use custom label or default
  const displayLabel = label ?? t(page ? getPageLoadingMessageKey(page) : getPageLoadingMessageKey('default'))

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <LoadingSpinner size="lg" label={displayLabel} />
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 motion-safe:animate-pulse motion-reduce:animate-none">
        {displayLabel}
      </p>
    </div>
  )
}

export function ButtonLoadingSpinner({
  className,
  label = 'Working on it...',
}: {
  className?: string
  /** Accessible label for the loading state */
  label?: string
}): React.ReactElement {
  return (
    <LoadingSpinner
      size="sm"
      {...(className !== undefined ? { className } : {})}
      color="currentColor"
      label={label}
    />
  )
}
