/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Skeleton loading component for database items
 * Provides visual feedback while database list loads
 */

import React from 'react'
import { t } from '@/i18n'

export function DatabaseItemSkeleton(): React.ReactElement {
  return (
    <div
      className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 motion-safe:animate-pulse motion-reduce:animate-none"
      role="status"
      aria-label={t('aria.skeletons.loadingDatabaseItem')}
    >
      <div className="flex items-center gap-4">
        {/* Logo/Icon placeholder */}
        <div className="w-10 h-10 bg-earth-200 dark:bg-earth-700 rounded flex-shrink-0" />

        {/* Info placeholder */}
        <div className="flex-1 min-w-0 space-y-2">
          <div className="h-5 bg-earth-200 dark:bg-earth-700 rounded w-2/3" />
          <div className="flex items-center gap-2">
            <div className="h-4 w-20 bg-earth-200 dark:bg-earth-700 rounded" />
            <div className="h-4 w-16 bg-earth-200 dark:bg-earth-700 rounded" />
          </div>
        </div>

        {/* Actions placeholder */}
        <div className="flex items-center gap-2 ml-4 flex-shrink-0">
          <div className="w-8 h-8 bg-earth-200 dark:bg-earth-700 rounded" />
          <div className="w-20 h-10 bg-earth-200 dark:bg-earth-700 rounded-lg" />
        </div>
      </div>
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function DatabaseItemSkeletonList({ count = 5 }: { count?: number }): React.ReactElement {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, index) => (
        <DatabaseItemSkeleton key={index} />
      ))}
    </div>
  )
}

export function DatabaseCardSkeleton(): React.ReactElement {
  return (
    <div
      className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 motion-safe:animate-pulse motion-reduce:animate-none"
      role="status"
      aria-label={t('aria.skeletons.loadingDatabase')}
    >
      <div className="flex items-start gap-3">
        {/* Logo placeholder */}
        <div className="w-12 h-12 bg-earth-200 dark:bg-earth-700 rounded flex-shrink-0" />

        <div className="flex-1 min-w-0 space-y-2">
          {/* Title */}
          <div className="h-5 bg-earth-200 dark:bg-earth-700 rounded w-3/4" />
          {/* Description */}
          <div className="space-y-1">
            <div className="h-3 bg-earth-200 dark:bg-earth-700 rounded w-full" />
            <div className="h-3 bg-earth-200 dark:bg-earth-700 rounded w-2/3" />
          </div>
          {/* Badge */}
          <div className="h-5 w-24 bg-earth-200 dark:bg-earth-700 rounded" />
        </div>
      </div>
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function DatabaseCardSkeletonGrid({ count = 6 }: { count?: number }): React.ReactElement {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, index) => (
        <DatabaseCardSkeleton key={index} />
      ))}
    </div>
  )
}

export default DatabaseItemSkeleton
