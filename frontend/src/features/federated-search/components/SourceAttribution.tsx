/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SourceAttribution Component
 *
 * Displays where a search result came from and shows relevant metadata
 * about each contributing source. Accessible with clear visual hierarchy.
 */

import React from 'react'
import { ExternalLink, Check } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import type { ResultAttribution } from '../types/federated-search.types'

// ==================== Types ====================

interface SourceAttributionProps {
  /** List of attributions for this result */
  attributions: ResultAttribution[]
  /** Whether to show metadata details */
  showMetadata?: boolean
  /** CSS class name */
  className?: string
}

// ==================== Component ====================

export function SourceAttribution({
  attributions,
  showMetadata = false,
  className,
}: SourceAttributionProps): React.ReactElement {
  if (!attributions || attributions.length === 0) {
    return <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">No source attribution available</div>
  }

  const primaryAttribution = attributions.find(attr => attr.isPrimary)! || attributions[0]
  const secondaryAttributions = attributions.filter(attr => !attr.isPrimary)

  return (
    <div className={clsx('space-y-2', className)}>
      {/* Primary Source */}
      <div className="flex items-start gap-2">
        <div className="flex-shrink-0">
          <Check className="w-4 h-4 text-status-success-600 mt-0.5" aria-hidden="true" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
              {formatSourceName(primaryAttribution.source)}
            </span>
            <span
              className="text-xs font-semibold px-2 py-1 rounded-full bg-status-success-100 dark:bg-status-success-900 text-status-success-800 dark:text-status-success-100"
              aria-label={`Relevance score ${primaryAttribution.score}%`}
            >
              {primaryAttribution.score}% match
            </span>
          </div>

          {/* Source URL Link */}
          {primaryAttribution.sourceUrl && (
            <a
              href={primaryAttribution.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-lsc-rose dark:text-lsc-rose-light hover:underline flex items-center gap-1 mt-1 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose rounded px-1"
              aria-label={`View on ${formatSourceName(primaryAttribution.source)} (opens in new tab)`}
            >
              View original <ExternalLink className="w-3 h-3" aria-hidden="true" />
            </a>
          )}

          {/* Metadata */}
          {showMetadata && primaryAttribution.sourceMetadata && (
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 space-y-1">
              {Object.entries(primaryAttribution.sourceMetadata).map(([key, value]) => (
                <div key={key} className="flex">
                  <span className="font-medium mr-2">{key}:</span>
                  <span className="break-words">{String(value)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Secondary Sources */}
      {secondaryAttributions.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-800 dark:hover:text-earth-200 flex items-center gap-1">
            <span>Also found in {secondaryAttributions.length} other source(s)</span>
            <span aria-hidden="true">▼</span>
          </summary>

          <div className="mt-2 space-y-2 pl-4 border-l-2 border-lsc-border dark:border-earth-700">
            {secondaryAttributions.map((attr, index) => (
              <div key={index} className="flex items-center justify-between gap-2">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{formatSourceName(attr.source)}</span>
                <span className="text-xs font-semibold px-2 py-1 rounded-full bg-earth-100 dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70">
                  {attr.score}%
                </span>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Fetched Timestamp */}
      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
        <time dateTime={primaryAttribution.fetchedAt}>
          Updated {formatRelativeTime(primaryAttribution.fetchedAt)}
        </time>
      </div>
    </div>
  )
}

// ==================== Utility Functions ====================

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

function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSeconds < 60) {
    return 'just now'
  }
  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`
  }
  if (diffHours < 24) {
    return `${diffHours}h ago`
  }
  if (diffDays < 7) {
    return `${diffDays}d ago`
  }

  return date.toLocaleDateString()
}

export default SourceAttribution
