/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Skeleton Loaders for Account Page
 *
 * Provides visual placeholders during loading that:
 * - Reduce perceived wait time
 * - Show the layout that will appear
 * - Use subtle animation (respects reduced motion)
 * - Maintain layout stability (no jumping)
 */
import React from 'react'
import { t } from '@/i18n'

interface SkeletonProps {
  className?: string
}

/**
 * Base skeleton element with pulse animation
 */
export const Skeleton: React.FC<SkeletonProps> = ({ className = '' }) => (
  <div
    className={`bg-sage/20 dark:bg-earth-700 motion-safe:animate-pulse rounded ${className}`}
    aria-hidden="true"
  />
)

/**
 * Skeleton for a single checkout/hold item card
 */
export const ItemCardSkeleton: React.FC = () => (
  <div className="p-4 rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800">
    <div className="flex items-start gap-4">
      {/* Book cover placeholder */}
      <Skeleton className="w-16 h-20 rounded-lg flex-shrink-0" />

      <div className="flex-1 min-w-0 space-y-3">
        {/* Title */}
        <Skeleton className="h-5 w-3/4" />
        {/* Author */}
        <Skeleton className="h-4 w-1/2" />
        {/* Date info */}
        <div className="flex gap-4">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>

      {/* Action button */}
      <Skeleton className="w-20 h-10 rounded-xl flex-shrink-0" />
    </div>
  </div>
)

/**
 * Skeleton for the overview stats cards
 */
export const StatsCardSkeleton: React.FC = () => (
  <div className="bg-cream dark:bg-earth-800 rounded-xl p-4">
    <div className="flex items-center gap-3 mb-3">
      <Skeleton className="w-10 h-10 rounded-xl" />
      <Skeleton className="h-4 w-24" />
    </div>
    <Skeleton className="h-8 w-16" />
  </div>
)

/**
 * Skeleton for the overview section
 */
export const OverviewSkeleton: React.FC = () => (
  <div className="space-y-6" aria-label={t('aria.account.loadingAccountOverview')} role="status">
    {/* Stats row */}
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <StatsCardSkeleton />
      <StatsCardSkeleton />
      <StatsCardSkeleton />
    </div>

    {/* Quick actions placeholder */}
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Skeleton className="h-32 rounded-xl" />
      <Skeleton className="h-32 rounded-xl" />
    </div>

    {/* Recent items */}
    <div className="space-y-3">
      <Skeleton className="h-6 w-40 mb-4" />
      <ItemCardSkeleton />
      <ItemCardSkeleton />
      <ItemCardSkeleton />
    </div>
  </div>
)

/**
 * Skeleton for the checkouts/holds list
 */
export const ListSkeleton: React.FC<{ count?: number }> = ({ count = 3 }) => (
  <div className="space-y-4" aria-label={t('aria.account.loadingItems')} role="status">
    {/* Header */}
    <div className="flex items-center justify-between mb-4">
      <Skeleton className="h-7 w-40" />
      <Skeleton className="h-10 w-24 rounded-xl" />
    </div>

    {/* Items */}
    {Array.from({ length: count }).map((_, i) => (
      <ItemCardSkeleton key={`list-skeleton-${i}`} />
    ))}
  </div>
)

/**
 * Skeleton for favorites/lists grid
 */
export const GridSkeleton: React.FC<{ count?: number }> = ({ count = 6 }) => (
  <div className="space-y-4" aria-label={t('aria.account.loadingItems')} role="status">
    {/* Header */}
    <div className="flex items-center justify-between mb-4">
      <Skeleton className="h-7 w-40" />
      <Skeleton className="h-10 w-24 rounded-xl" />
    </div>

    {/* Grid */}
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={`grid-skeleton-${i}`} className="rounded-xl border-2 border-sage/20 dark:border-earth-700 p-4">
          <Skeleton className="w-full aspect-[3/4] rounded-lg mb-3" />
          <Skeleton className="h-4 w-3/4 mb-2" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      ))}
    </div>
  </div>
)

/**
 * Skeleton for notification preferences
 */
export const NotificationsSkeleton: React.FC = () => (
  <div className="space-y-6" aria-label={t('aria.account.loadingNotificationPreferences')} role="status">
    <div className="space-y-3">
      <Skeleton className="h-7 w-48 mb-4" />
      <Skeleton className="h-5 w-64 mb-6" />
    </div>

    <div className="p-6 bg-cream dark:bg-earth-800 rounded-xl space-y-4">
      <Skeleton className="h-6 w-40 mb-4" />
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={`notification-skeleton-${i}`} className="flex items-center gap-4">
          <Skeleton className="w-12 h-7 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-64" />
          </div>
        </div>
      ))}
    </div>
  </div>
)

/**
 * Skeleton for security/sessions
 */
export const SecuritySkeleton: React.FC = () => (
  <div className="space-y-6" aria-label={t('aria.account.loadingSecuritySettings')} role="status">
    {/* Password section */}
    <div className="p-6 bg-cream dark:bg-earth-800 rounded-xl space-y-4">
      <Skeleton className="h-6 w-40 mb-4" />
      <Skeleton className="h-10 w-full rounded-xl" />
      <Skeleton className="h-10 w-full rounded-xl" />
      <Skeleton className="h-10 w-full rounded-xl" />
      <Skeleton className="h-10 w-40 rounded-xl" />
    </div>

    {/* Sessions section */}
    <div className="p-6 bg-cream dark:bg-earth-800 rounded-xl space-y-4">
      <Skeleton className="h-6 w-32 mb-4" />
      {Array.from({ length: 2 }).map((_, i) => (
        <div key={`session-skeleton-${i}`} className="p-4 rounded-xl border-2 border-sage/20 dark:border-earth-700">
          <div className="flex items-center gap-4">
            <Skeleton className="w-10 h-10 rounded-lg" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-24" />
            </div>
            <Skeleton className="w-16 h-8 rounded-xl" />
          </div>
        </div>
      ))}
    </div>
  </div>
)

/**
 * Simple inline loading message for accessibility
 */
export const LoadingMessage: React.FC<{ message?: string }> = ({ message = 'Loading...' }) => (
  <div className="flex flex-col items-center justify-center py-12 gap-4" role="status" aria-live="polite">
    <div className="w-12 h-12 rounded-full border-4 border-sage/20 border-t-lsc-rose motion-safe:animate-spin" />
    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center">
      {message}
    </p>
    <span className="sr-only">{message}</span>
  </div>
)
