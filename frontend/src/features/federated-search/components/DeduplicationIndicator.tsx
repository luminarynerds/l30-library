/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * DeduplicationIndicator Component
 *
 * Shows when a search result was merged from multiple sources
 * and displays the confidence score for the merge
 */

import React from 'react'
import { Merge } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import type { DeduplicationInfo } from '../types/federated-search.types'
import { t } from '@/i18n'

// ==================== Types ====================

interface DeduplicationIndicatorProps {
  /** Deduplication information */
  dedup: DeduplicationInfo
  /** Show detailed information in tooltip/popover */
  showDetails?: boolean
  /** CSS class name */
  className?: string
}

// ==================== Component ====================

export function DeduplicationIndicator({
  dedup,
  showDetails = true,
  className,
}: DeduplicationIndicatorProps): React.ReactElement | null {
  if (!dedup.merged || dedup.matchCount < 2) {
    return null
  }

  const confidenceLevel = getConfidenceLevel(dedup.confidence)
  const confidenceColor = getConfidenceColor(confidenceLevel)

  return (
    <div className={className}>
      {showDetails ? (
        <details className="inline-block">
          <summary
            className={clsx(
              'cursor-pointer inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg font-medium text-sm transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose',
              'hover:opacity-80',
              confidenceColor.bg,
              confidenceColor.text
            )}
            aria-label={`Result merged from ${dedup.matchCount} sources with ${dedup.confidence}% confidence`}
          >
            <Merge className="w-4 h-4" aria-hidden="true" />
            <span>Merged ({dedup.matchCount})</span>
            <span aria-hidden="true" className="text-xs">
              ▼
            </span>
          </summary>

          {/* Expanded Details */}
          <div
            className={clsx(
              'absolute z-10 mt-1 bg-lsc-white dark:bg-earth-900 rounded-lg shadow-lg border border-lsc-border dark:border-earth-700 p-3 min-w-max'
            )}
            role="region"
            aria-label={t('aria.federated-search.deduplicationDetails')}
          >
            {/* Confidence Score */}
            <div className="mb-3 pb-3 border-b border-lsc-border dark:border-earth-700">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                  Match Confidence
                </span>
                <span className={clsx('text-sm font-bold', confidenceColor.text)}>
                  {dedup.confidence}%
                </span>
              </div>

              {/* Confidence Bar */}
              <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-2 overflow-hidden">
                <div
                  className={clsx('h-full transition-all', confidenceColor.bg)}
                  style={{ width: `${dedup.confidence}%` }}
                  role="progressbar"
                  aria-valuenow={dedup.confidence}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`${dedup.confidence}% confidence`}
                />
              </div>

              {/* Interpretation */}
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {getConfidenceMessage(dedup.confidence)}
              </p>
            </div>

            {/* Sources List */}
            <div>
              <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                Found in {dedup.matchCount} sources:
              </p>
              <ul className="space-y-1">
                {dedup.matchedSources.map(source => (
                  <li
                    key={source}
                    className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-2"
                  >
                    <span className="w-1.5 h-1.5 bg-earth-500 rounded-full" aria-hidden="true" />
                    {formatSourceName(source)}
                  </li>
                ))}
              </ul>
            </div>

            {/* Merge Reason */}
            {dedup.mergeReason && (
              <div className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700">
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  <strong>Reason:</strong> {dedup.mergeReason}
                </p>
              </div>
            )}
          </div>
        </details>
      ) : (
        /* Simple Badge Version */
        <div
          className={clsx(
            'inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg font-medium text-sm',
            confidenceColor.bg,
            confidenceColor.text
          )}
          title={`Merged from ${dedup.matchCount} sources with ${dedup.confidence}% confidence`}
          aria-label={`Result merged from ${dedup.matchCount} sources with ${dedup.confidence}% confidence`}
        >
          <Merge className="w-4 h-4" aria-hidden="true" />
          <span>Merged ({dedup.matchCount})</span>
          <span className="text-xs opacity-75">{dedup.confidence}%</span>
        </div>
      )}
    </div>
  )
}

// ==================== Utility Functions ====================

function getConfidenceLevel(confidence: number): 'high' | 'medium' | 'low' {
  if (confidence >= 80) return 'high'
  if (confidence >= 60) return 'medium'
  return 'low'
}

function getConfidenceColor(level: 'high' | 'medium' | 'low'): {
  bg: string
  text: string
} {
  const colors = {
    high: {
      bg: 'bg-status-success-100 dark:bg-status-success-900/30',
      text: 'text-status-success-700 dark:text-status-success-300',
    },
    medium: {
      bg: 'bg-status-warning-100 dark:bg-status-warning-900/30',
      text: 'text-status-warning-700 dark:text-status-warning-300',
    },
    low: {
      bg: 'bg-status-warning-100 dark:bg-status-warning-900/30',
      text: 'text-status-warning-700 dark:text-status-warning-300',
    },
  }
  return colors[level]
}

function getConfidenceMessage(confidence: number): string {
  if (confidence >= 90) return 'Highly confident this is the same resource'
  if (confidence >= 80) return 'Confident this is the same resource'
  if (confidence >= 70) return 'Likely the same resource'
  if (confidence >= 60) return 'Possibly the same resource'
  return 'Low confidence - may be different resources'
}

function formatSourceName(source: string): string {
  const names: Record<string, string> = {
    'local-catalog': 'Local Catalog',
    'open-library': 'Open Library',
    'google-books': 'Google Books',
    'worldcat': 'WorldCat',
    'isbn-search': 'ISBN Search',
  }
  return names[source] || source
}

export default DeduplicationIndicator
