/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Skeleton loading components for Staff pages
 * Provides visual feedback while staff content loads
 *
 * Features:
 * - Staff dashboard skeleton with sidebar
 * - Staff table/list skeletons
 * - Stats panel skeletons
 * - Shimmer animation (respects reduced motion)
 */

import React from 'react'
import { t } from '@/i18n'

export function StaffStatsCardsSkeleton({ count = 4 }: { count?: number }): React.ReactElement {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm"
        >
          <div className="flex items-start justify-between mb-4">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-earth-700 rounded-xl motion-safe:animate-pulse motion-reduce:animate-none" />
            <div className="w-16 h-4 bg-lsc-cream dark:bg-earth-700 rounded motion-safe:animate-pulse motion-reduce:animate-none" />
          </div>
          <div className="space-y-2">
            <div className="h-8 bg-lsc-cream dark:bg-earth-700 rounded w-20 motion-safe:animate-pulse motion-reduce:animate-none" />
            <div className="h-4 bg-lsc-cream dark:bg-earth-700 rounded w-32 motion-safe:animate-pulse motion-reduce:animate-none" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function StaffListItemSkeleton(): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
      <div className="flex items-center gap-4">
        {/* Avatar/Icon placeholder */}
        <div className="w-12 h-12 bg-lsc-cream dark:bg-earth-700 rounded-full flex-shrink-0 motion-safe:animate-pulse motion-reduce:animate-none" />

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-2">
          <div className="h-5 bg-lsc-cream dark:bg-earth-700 rounded w-1/3 motion-safe:animate-pulse motion-reduce:animate-none" />
          <div className="flex gap-3">
            <div className="h-4 w-24 bg-lsc-cream dark:bg-earth-700 rounded motion-safe:animate-pulse motion-reduce:animate-none" />
            <div className="h-4 w-20 bg-lsc-cream dark:bg-earth-700 rounded motion-safe:animate-pulse motion-reduce:animate-none" />
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 flex-shrink-0">
          <div className="w-8 h-8 bg-lsc-cream dark:bg-earth-700 rounded-xl motion-safe:animate-pulse motion-reduce:animate-none" />
          <div className="w-8 h-8 bg-lsc-cream dark:bg-earth-700 rounded-xl motion-safe:animate-pulse motion-reduce:animate-none" />
        </div>
      </div>
    </div>
  )
}

export function StaffListSkeleton({ count = 5 }: { count?: number }): React.ReactElement {
  return (
    <div className="space-y-3" role="status" aria-label={t('aria.account.loadingItems')}>
      {Array.from({ length: count }).map((_, index) => (
        <StaffListItemSkeleton key={index} />
      ))}
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function StaffPageWithTabsSkeleton(): React.ReactElement {
  return (
    <div className="space-y-6" role="status" aria-label={t('aria.appRoutes.loadingPage')}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="h-8 w-64 bg-lsc-cream dark:bg-earth-700 rounded-xl motion-safe:animate-pulse motion-reduce:animate-none" />
        <div className="h-10 w-32 bg-lsc-cream dark:bg-earth-700 rounded-xl motion-safe:animate-pulse motion-reduce:animate-none" />
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-lsc-border dark:border-earth-700">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-10 w-24 bg-lsc-cream dark:bg-earth-700 rounded-t-xl motion-safe:animate-pulse motion-reduce:animate-none"
          />
        ))}
      </div>

      {/* Stats cards */}
      <StaffStatsCardsSkeleton />

      {/* Content area */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-6">
            <div className="h-6 w-40 bg-lsc-cream dark:bg-earth-700 rounded motion-safe:animate-pulse motion-reduce:animate-none" />
            <div className="flex gap-2">
              <div className="h-10 w-32 bg-lsc-cream dark:bg-earth-700 rounded-xl motion-safe:animate-pulse motion-reduce:animate-none" />
              <div className="h-10 w-24 bg-lsc-cream dark:bg-earth-700 rounded-xl motion-safe:animate-pulse motion-reduce:animate-none" />
            </div>
          </div>
          <StaffListSkeleton count={5} />
        </div>
      </div>

      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function StaffDashboardPanelSkeleton(): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
      {/* Panel header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-lsc-cream dark:bg-earth-700 rounded-xl motion-safe:animate-pulse motion-reduce:animate-none" />
          <div className="h-6 w-40 bg-lsc-cream dark:bg-earth-700 rounded motion-safe:animate-pulse motion-reduce:animate-none" />
        </div>
        <div className="w-20 h-8 bg-lsc-cream dark:bg-earth-700 rounded-xl motion-safe:animate-pulse motion-reduce:animate-none" />
      </div>

      {/* Panel content - list of items */}
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="flex items-center justify-between p-3 border border-lsc-border dark:border-earth-700 rounded-xl">
            <div className="flex-1 space-y-2">
              <div className="h-4 w-3/4 bg-lsc-cream dark:bg-earth-700 rounded motion-safe:animate-pulse motion-reduce:animate-none" />
              <div className="h-3 w-1/2 bg-lsc-cream dark:bg-earth-700 rounded motion-safe:animate-pulse motion-reduce:animate-none" />
            </div>
            <div className="w-16 h-8 bg-lsc-cream dark:bg-earth-700 rounded-xl motion-safe:animate-pulse motion-reduce:animate-none" />
          </div>
        ))}
      </div>
    </div>
  )
}

export default StaffListSkeleton
