/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Skeleton Component
 *
 * A loading placeholder that respects reduced motion preferences.
 * Shows a subtle pulse animation when motion is allowed,
 * and a static placeholder when motion is reduced.
 *
 * Uses Tailwind's motion-reduce/motion-safe variants to automatically
 * adapt to user preferences.
 *
 * @example
 * // Basic text skeleton
 * <Skeleton className="h-4 w-48" />
 *
 * // Card skeleton
 * <Skeleton variant="card" />
 *
 * // Avatar skeleton
 * <Skeleton variant="avatar" size="lg" />
 */

import { clsx } from '@/utils/helpers'
import { useTranslation } from '@/i18n/I18nContext'

interface SkeletonProps {
  /** Custom className for size and additional styling */
  className?: string
  /** Predefined variant shapes */
  variant?: 'text' | 'card' | 'avatar' | 'button' | 'image'
  /** Size for avatar and button variants */
  size?: 'sm' | 'md' | 'lg'
  /** Animation style: 'pulse' (default) or 'shimmer' (directional sweep) */
  animation?: 'pulse' | 'shimmer'
}

const variantClasses = {
  text: 'h-4 rounded',
  card: 'h-48 rounded-xl',
  avatar: '',
  button: 'rounded-xl',
  image: 'rounded-lg aspect-video',
}

const avatarSizes = {
  sm: 'w-8 h-8',
  md: 'w-10 h-10',
  lg: 'w-12 h-12',
}

const buttonSizes = {
  sm: 'h-8 w-20',
  md: 'h-10 w-24',
  lg: 'h-12 w-32',
}

export default function Skeleton({
  className,
  variant = 'text',
  size = 'md',
  animation = 'pulse',
}: SkeletonProps): React.ReactElement {
  const { t } = useTranslation()
  const baseClasses = clsx(
    // Animation style
    animation === 'shimmer'
      ? 'skeleton-shimmer'
      : [
          'bg-lsc-border dark:bg-earth-700',
          'motion-safe:animate-pulse',
          'motion-reduce:animate-none',
        ],
    // Variant-specific classes
    variantClasses[variant],
    // Size classes for specific variants
    variant === 'avatar' && `rounded-full ${avatarSizes[size]}`,
    variant === 'button' && buttonSizes[size],
    className
  )

  return (
    <div
      role="status"
      aria-label={t('common.loading')}
      className={baseClasses}
    >
      <span className="sr-only">{t('common.loading')}</span>
    </div>
  )
}

export function SkeletonCard(): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 space-y-4">
      <Skeleton className="h-40 w-full" variant="image" />
      <Skeleton className="h-6 w-3/4" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  )
}

export function SkeletonText({
  lines = 3,
}: {
  lines?: number
}): React.ReactElement {
  return (
    <div className="space-y-3">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={clsx(
            'h-4',
            // Vary the width for a more natural look
            i === lines - 1 ? 'w-4/5' : 'w-full'
          )}
        />
      ))}
    </div>
  )
}

export function SkeletonList({
  items = 3,
}: {
  items?: number
}): React.ReactElement {
  return (
    <div className="space-y-4">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-4">
          <Skeleton variant="avatar" size="md" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  )
}
