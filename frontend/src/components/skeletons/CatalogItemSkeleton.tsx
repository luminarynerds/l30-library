/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Skeleton loading component for catalog items
 * Provides visual feedback while content loads
 */

import React from 'react'
import { t } from '@/i18n'

export function CatalogItemSkeleton(): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-5 motion-safe:animate-pulse motion-reduce:animate-none" role="status" aria-label={t('aria.skeletons.loadingCatalogItem')}>
      <div className="flex gap-4">
        {/* Cover placeholder — matches CatalogListCard cover dimensions (w-20, h-[120px]) */}
        <div className="w-20 h-[120px] bg-lsc-cream dark:bg-lsc-brown rounded flex-shrink-0" />

        {/* Content placeholder */}
        <div className="flex-1 min-w-0 space-y-3">
          {/* Title */}
          <div className="h-5 bg-lsc-cream dark:bg-lsc-brown rounded w-3/4" />

          {/* Author */}
          <div className="h-4 bg-lsc-cream dark:bg-lsc-brown rounded w-1/2" />

          {/* Badges */}
          <div className="flex gap-2">
            <div className="h-6 w-16 bg-lsc-cream dark:bg-lsc-brown rounded" />
            <div className="h-6 w-20 bg-lsc-cream dark:bg-lsc-brown rounded" />
            <div className="h-6 w-24 bg-lsc-cream dark:bg-lsc-brown rounded" />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <div className="h-3 bg-lsc-cream dark:bg-lsc-brown rounded w-full" />
            <div className="h-3 bg-lsc-cream dark:bg-lsc-brown rounded w-4/5" />
          </div>
        </div>
      </div>
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function CatalogItemSkeletonList({ count = 5 }: { count?: number }): React.ReactElement {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, index) => (
        <CatalogItemSkeleton key={index} />
      ))}
    </div>
  )
}

export function CatalogItemSkeletonGrid({ count = 8 }: { count?: number }): React.ReactElement {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-[18px]">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="motion-safe:animate-pulse motion-reduce:animate-none" role="status" aria-label={t('aria.skeletons.loadingCatalogItem')}>
          <div className="w-full aspect-[2/3] rounded-xl bg-lsc-cream dark:bg-lsc-brown mb-2" />
          <div className="h-4 bg-lsc-cream dark:bg-lsc-brown rounded w-3/4 mb-1" />
          <div className="h-3 bg-lsc-cream dark:bg-lsc-brown rounded w-1/2" />
          <span className="sr-only">Loading...</span>
        </div>
      ))}
    </div>
  )
}

export default CatalogItemSkeleton
