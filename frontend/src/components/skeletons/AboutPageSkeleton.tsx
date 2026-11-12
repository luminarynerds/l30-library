/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Skeleton loading components for About Us page sections
 * Provides visual feedback while content loads
 */

import React from 'react'
import { t } from '@/i18n'

export function InfoCardSkeleton(): React.ReactElement {
  return (
    <div
      className="bg-lsc-cream dark:bg-lsc-dark/20 rounded-xl p-6 border border-lsc-border dark:border-earth-700 motion-safe:animate-pulse motion-reduce:animate-none"
      role="status"
      aria-label={t('aria.skeletons.loadingContent')}
    >
      <div className="space-y-3">
        {/* Title */}
        <div className="h-6 bg-lsc-border dark:bg-earth-700 rounded w-1/2" />
        {/* Description */}
        <div className="space-y-2">
          <div className="h-4 bg-lsc-border dark:bg-earth-700 rounded w-full" />
          <div className="h-4 bg-lsc-border dark:bg-earth-700 rounded w-3/4" />
        </div>
        {/* Meta info */}
        <div className="flex flex-wrap gap-4 pt-2">
          <div className="h-4 w-24 bg-lsc-border dark:bg-earth-700 rounded" />
          <div className="h-4 w-20 bg-lsc-border dark:bg-earth-700 rounded" />
        </div>
      </div>
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function StaffBioSkeleton(): React.ReactElement {
  return (
    <div
      className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 motion-safe:animate-pulse motion-reduce:animate-none"
      role="status"
      aria-label={t('aria.skeletons.loadingStaffBio')}
    >
      <div className="flex gap-4">
        {/* Avatar placeholder */}
        <div className="w-20 h-20 rounded-full bg-lsc-cream dark:bg-lsc-brown flex-shrink-0" />
        {/* Info */}
        <div className="flex-1 space-y-2">
          <div className="h-5 bg-lsc-border dark:bg-earth-700 rounded w-1/2" />
          <div className="h-4 bg-lsc-border dark:bg-earth-700 rounded w-1/3" />
          <div className="h-3 bg-lsc-border dark:bg-earth-700 rounded w-1/4" />
        </div>
      </div>
      {/* Bio text */}
      <div className="mt-4 space-y-2">
        <div className="h-3 bg-lsc-border dark:bg-earth-700 rounded w-full" />
        <div className="h-3 bg-lsc-border dark:bg-earth-700 rounded w-full" />
        <div className="h-3 bg-lsc-border dark:bg-earth-700 rounded w-2/3" />
      </div>
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function StaffBioSkeletonGrid({ count = 4 }: { count?: number }): React.ReactElement {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      {Array.from({ length: count }).map((_, index) => (
        <StaffBioSkeleton key={index} />
      ))}
    </div>
  )
}

export default InfoCardSkeleton
