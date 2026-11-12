/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Skeleton loading component for event cards
 * Provides visual feedback while content loads
 */

import React from 'react'
import { t } from '@/i18n'

export function EventCardSkeleton(): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-5 motion-safe:animate-pulse motion-reduce:animate-none" role="status" aria-label={t('aria.skeletons.loadingEvent')}>
      <div className="flex gap-4">
        {/* Date box placeholder */}
        <div className="w-16 h-16 bg-lsc-cream dark:bg-earth-800 rounded-xl flex-shrink-0" />

        {/* Content placeholder */}
        <div className="flex-1 min-w-0 space-y-3">
          {/* Title */}
          <div className="h-6 bg-lsc-cream dark:bg-lsc-brown rounded w-3/4" />

          {/* Meta info */}
          <div className="flex gap-3">
            <div className="h-4 w-20 bg-lsc-cream dark:bg-lsc-brown rounded" />
            <div className="h-4 w-24 bg-lsc-cream dark:bg-lsc-brown rounded" />
            <div className="h-4 w-16 bg-lsc-cream dark:bg-lsc-brown rounded" />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <div className="h-3 bg-lsc-cream dark:bg-lsc-brown rounded w-full" />
            <div className="h-3 bg-lsc-cream dark:bg-lsc-brown rounded w-5/6" />
          </div>

          {/* Badges */}
          <div className="flex gap-2">
            <div className="h-6 w-20 bg-lsc-cream dark:bg-lsc-brown rounded" />
            <div className="h-6 w-32 bg-lsc-cream dark:bg-lsc-brown rounded" />
          </div>
        </div>

        {/* Button placeholder */}
        <div className="w-24 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex-shrink-0" />
      </div>
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function EventCardSkeletonList({ count = 5 }: { count?: number }): React.ReactElement {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, index) => (
        <EventCardSkeleton key={index} />
      ))}
    </div>
  )
}

export default EventCardSkeleton
