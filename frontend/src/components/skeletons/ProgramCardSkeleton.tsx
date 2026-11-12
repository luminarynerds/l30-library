/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { t } from '@/i18n'

export function ProgramCardSkeleton(): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-5 motion-safe:animate-pulse motion-reduce:animate-none" role="status" aria-label={t('aria.skeletons.loadingProgram')}>
      <div className="space-y-3">
        {/* Type badge */}
        <div className="h-5 bg-lsc-cream dark:bg-lsc-brown rounded-full w-28" />

        {/* Title */}
        <div className="space-y-2">
          <div className="h-6 bg-lsc-cream dark:bg-lsc-brown rounded w-4/5" />
        </div>

        {/* Description */}
        <div className="space-y-1.5">
          <div className="h-3.5 bg-lsc-cream dark:bg-lsc-brown rounded w-full" />
          <div className="h-3.5 bg-lsc-cream dark:bg-lsc-brown rounded w-5/6" />
        </div>

        {/* Compact meta row */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <div className="h-3.5 bg-lsc-cream dark:bg-lsc-brown rounded w-32" />
          <div className="h-3.5 bg-lsc-cream dark:bg-lsc-brown rounded w-20" />
          <div className="h-3.5 bg-lsc-cream dark:bg-lsc-brown rounded w-24" />
        </div>

        {/* Button */}
        <div className="h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl w-full" />
      </div>
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function ProgramCardSkeletonGrid({ count = 4 }: { count?: number }): React.ReactElement {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {Array.from({ length: count }).map((_, index) => (
        <ProgramCardSkeleton key={index} />
      ))}
    </div>
  )
}

export default ProgramCardSkeleton
