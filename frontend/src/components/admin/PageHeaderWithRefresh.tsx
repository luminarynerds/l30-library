/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { RefreshCw } from 'lucide-react'
import { clsx } from '../../utils/helpers'

export interface PageHeaderWithRefreshProps {
  title: string
  subtitle?: string
  icon?: React.ElementType
  onRefresh?: () => void
  refreshing?: boolean
  actions?: React.ReactNode
}

export function PageHeaderWithRefresh({
  title,
  subtitle,
  icon: Icon,
  onRefresh,
  refreshing = false,
  actions,
}: PageHeaderWithRefreshProps): React.ReactElement {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
      <div className="flex items-start gap-3 min-w-0">
        {Icon && (
          <div className="p-2 rounded-lg bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose-light/15 dark:text-lsc-rose-light shrink-0">
            <Icon className="h-6 w-6" aria-hidden="true" />
          </div>
        )}
        <div className="min-w-0">
          <h1 className="font-serif text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream truncate">
            {title}
          </h1>
          {subtitle && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {actions}
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-lg border border-lsc-border px-3 py-1.5 text-sm text-lsc-dark/80 hover:bg-lsc-cream disabled:opacity-50 dark:border-earth-700 dark:text-lsc-cream/80 dark:hover:bg-earth-700"
          >
            <RefreshCw
              className={clsx('h-4 w-4', refreshing && 'motion-safe:animate-spin')}
              aria-hidden="true"
            />
            Refresh
          </button>
        )}
      </div>
    </div>
  )
}
