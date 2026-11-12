/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'

// Palette synced 2026-05-17: accepts both literal color names (green/blue/amber/…)
// and semantic aliases (success/accent/warning/danger/category) so call sites
// that mix the two vocabularies continue to render without runtime branches.
export type StatCardColor =
  | 'green' | 'blue' | 'amber' | 'purple' | 'red' | 'earth' | 'orange'
  | 'success' | 'accent' | 'warning' | 'danger' | 'category'

export interface StatCardProps {
  title: string
  value: number | string
  icon: React.ElementType
  color?: StatCardColor
  subtext?: string
}

const COLOR_CLASSES: Record<StatCardColor, string> = {
  green: 'bg-status-success-50 dark:bg-status-success-900/20 text-status-success-600 dark:text-status-success-400',
  blue: 'bg-earth-50 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light',
  amber: 'bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-600 dark:text-status-warning-400',
  purple: 'bg-category-50 dark:bg-category-900/20 text-category-600 dark:text-category-400',
  red: 'bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-600 dark:text-status-danger-400',
  earth: 'bg-earth-100 dark:bg-earth-700/30 text-lsc-dark/70 dark:text-lsc-cream/70',
  orange: 'bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-600 dark:text-status-warning-400',
  // Semantic aliases mapping to the literal palette above
  success: 'bg-status-success-50 dark:bg-status-success-900/20 text-status-success-600 dark:text-status-success-400',
  accent: 'bg-earth-50 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light',
  warning: 'bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-600 dark:text-status-warning-400',
  danger: 'bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-600 dark:text-status-danger-400',
  category: 'bg-category-50 dark:bg-category-900/20 text-category-600 dark:text-category-400',
}

export function StatCard({
  title,
  value,
  icon: Icon,
  color = 'blue',
  subtext,
}: StatCardProps): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${COLOR_CLASSES[color]}`}>
          <Icon className="h-6 w-6" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{title}</p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</p>
          {subtext && (
            <p className="text-xs text-earth-600 dark:text-earth-400 mt-0.5">{subtext}</p>
          )}
        </div>
      </div>
    </div>
  )
}

export interface StatGridProps {
  children: React.ReactNode
  columns?: 2 | 3 | 4 | 5 | 6
}

const GRID_COLS: Record<NonNullable<StatGridProps['columns']>, string> = {
  2: 'grid-cols-1 sm:grid-cols-2',
  3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
  4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
  5: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-5',
  6: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6',
}

export function StatGrid({ children, columns = 4 }: StatGridProps): React.ReactElement {
  return <div className={`grid gap-4 ${GRID_COLS[columns]}`}>{children}</div>
}
