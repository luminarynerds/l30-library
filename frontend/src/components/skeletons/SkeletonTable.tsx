/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Skeleton loading component for tables
 * Provides visual feedback while table data loads
 *
 * Features:
 * - Configurable rows and columns
 * - Shimmer animation (respects reduced motion)
 * - Accessible with aria-label
 * - Matches table layout patterns
 */

import React from 'react'
import { t } from '@/i18n'

interface SkeletonTableProps {
  /** Number of rows to display */
  rows?: number
  /** Number of columns to display */
  columns?: number
  /** Show table header skeleton */
  showHeader?: boolean
  /** Show action column (typically narrower) */
  showActions?: boolean
  /** Custom aria label */
  ariaLabel?: string
}

export function SkeletonTable({
  rows = 5,
  columns = 4,
  showHeader = true,
  showActions = false,
  ariaLabel = 'Loading table data',
}: SkeletonTableProps): React.ReactElement {
  const totalColumns = showActions ? columns + 1 : columns

  return (
    <div
      className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden"
      role="status"
      aria-label={ariaLabel}
    >
      <div className="overflow-x-auto">
        <table className="w-full">
          {showHeader && (
            <thead className="bg-lsc-cream/30 dark:bg-earth-700/30">
              <tr>
                {Array.from({ length: totalColumns }).map((_, colIndex) => (
                  <th key={colIndex} className="px-6 py-4 text-left">
                    <div
                      className={`h-4 bg-lsc-cream dark:bg-earth-700 rounded motion-safe:animate-pulse motion-reduce:animate-none ${
                        colIndex === totalColumns - 1 && showActions
                          ? 'w-16'
                          : colIndex === 0
                          ? 'w-32'
                          : 'w-24'
                      }`}
                    />
                  </th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {Array.from({ length: rows }).map((_, rowIndex) => (
              <tr
                key={rowIndex}
                className="border-t border-lsc-border dark:border-earth-700"
              >
                {Array.from({ length: totalColumns }).map((_, colIndex) => (
                  <td key={colIndex} className="px-6 py-4">
                    <div
                      className={`h-4 bg-lsc-cream dark:bg-earth-700 rounded motion-safe:animate-pulse motion-reduce:animate-none ${
                        colIndex === totalColumns - 1 && showActions
                          ? 'w-20'
                          : colIndex === 0
                          ? 'w-3/4'
                          : 'w-2/3'
                      }`}
                      style={{
                        // Stagger animation slightly for visual interest
                        animationDelay: `${(rowIndex * 50 + colIndex * 100) % 500}ms`,
                      }}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export function SkeletonTableCompact({
  rows = 3,
  columns = 3,
}: Pick<SkeletonTableProps, 'rows' | 'columns'>): React.ReactElement {
  return (
    <div
      className="space-y-2"
      role="status"
      aria-label={t('aria.skeletons.loadingData')}
    >
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4 items-center">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <div
              key={colIndex}
              className={`h-4 bg-lsc-cream dark:bg-earth-700 rounded motion-safe:animate-pulse motion-reduce:animate-none ${
                colIndex === 0 ? 'flex-1' : 'w-24'
              }`}
              style={{
                animationDelay: `${(rowIndex * 50 + colIndex * 100) % 500}ms`,
              }}
            />
          ))}
        </div>
      ))}
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export default SkeletonTable
