/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'

export interface ChangesSummaryChange {
  before: string | number
  after: string | number
}

export interface ChangesSummaryBannerProps {
  changes: Record<string, ChangesSummaryChange>
  fieldLabels?: Record<string, string>
  title?: string
}

export function ChangesSummaryBanner({
  changes,
  fieldLabels,
  title = 'Changes Summary',
}: ChangesSummaryBannerProps): React.ReactElement | null {
  const entries = Object.entries(changes)
  if (entries.length === 0) return null

  return (
    <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded p-4">
      <h4 className="text-sm font-semibold text-status-warning-900 dark:text-status-warning-100 mb-2">{title}</h4>
      <div className="space-y-1 text-sm text-status-warning-800 dark:text-status-warning-200">
        {entries.map(([key, { before, after }]) => (
          <div key={key} className="flex items-center gap-2 font-mono text-xs flex-wrap">
            <span className="font-semibold">{fieldLabels?.[key] ?? key}:</span>
            <span className="text-status-danger-700 dark:text-status-danger-300">{before}</span>
            <span aria-hidden="true">→</span>
            <span className="text-status-success-700 dark:text-status-success-300">{after}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
