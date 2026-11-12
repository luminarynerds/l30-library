/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Skeleton loading component for workshop/event cards
 * Used on Business Resources page and similar workshop listings
 */

import React from 'react'
import { t } from '@/i18n'

export function WorkshopCardSkeleton(): React.ReactElement {
  return (
    <div
      className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 motion-safe:animate-pulse motion-reduce:animate-none"
      role="status"
      aria-label={t('aria.skeletons.loadingWorkshop')}
    >
      <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4">
        <div className="flex-1 space-y-3">
          {/* Audience badge */}
          <div className="h-4 w-16 bg-lsc-border dark:bg-earth-700 rounded" />
          {/* Title */}
          <div className="h-6 bg-lsc-border dark:bg-earth-700 rounded w-3/4" />
          {/* Description */}
          <div className="space-y-2">
            <div className="h-4 bg-lsc-border dark:bg-earth-700 rounded w-full" />
            <div className="h-4 bg-lsc-border dark:bg-earth-700 rounded w-2/3" />
          </div>
          {/* Meta info (date, time, location, spots) */}
          <div className="flex flex-wrap gap-4 pt-1">
            <div className="h-4 w-32 bg-lsc-border dark:bg-earth-700 rounded" />
            <div className="h-4 w-24 bg-lsc-border dark:bg-earth-700 rounded" />
            <div className="h-4 w-28 bg-lsc-border dark:bg-earth-700 rounded" />
            <div className="h-4 w-20 bg-lsc-border dark:bg-earth-700 rounded" />
          </div>
        </div>
        {/* Register button */}
        <div className="w-24 h-10 bg-lsc-border dark:bg-earth-700 rounded-xl flex-shrink-0" />
      </div>
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function WorkshopCardSkeletonList({ count = 3 }: { count?: number }): React.ReactElement {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, index) => (
        <WorkshopCardSkeleton key={index} />
      ))}
    </div>
  )
}

export default WorkshopCardSkeleton
