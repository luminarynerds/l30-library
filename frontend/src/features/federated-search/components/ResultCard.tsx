/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * ResultCard Component
 *
 * Individual search result card showing item details with source attribution
 */

import React from 'react'
import { Star, BookOpen } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import SourceAttribution from './SourceAttribution'
import DeduplicationIndicator from './DeduplicationIndicator'
import type { FederatedSearchResult } from '../types/federated-search.types'

// ==================== Types ====================

interface ResultCardProps {
  /** Search result to display */
  result: FederatedSearchResult
  /** Called when result is clicked */
  onClick?: (result: FederatedSearchResult) => void
  /** Show source attribution */
  showAttribution?: boolean
  /** Show deduplication info */
  showDeduplication?: boolean
  /** CSS class name */
  className?: string
}

// ==================== Component ====================

export function ResultCard({
  result,
  onClick,
  showAttribution = true,
  showDeduplication = true,
  className,
}: ResultCardProps): React.ReactElement {
  const handleClick = () => {
    onClick?.(result)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick()
    }
  }

  return (
    <article
      className={clsx(
        'p-5 rounded-xl border border-lsc-border dark:border-earth-700 transition-all',
        'bg-lsc-white dark:bg-earth-800 hover:shadow-md hover:border-lsc-border dark:border-earth-700 dark:hover:border-earth-600',
        'focus-within:ring-2 focus-within:ring-lsc-rose',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={handleClick}
      role={onClick ? 'button' : 'article'}
      tabIndex={onClick ? 0 : -1}
      onKeyDown={onClick ? handleKeyDown : undefined}
    >
      {/* Header Section */}
      <div className="flex gap-4 mb-3">
        {/* Cover Image */}
        {result.coverUrl && (
          <div className="flex-shrink-0">
            <img
              src={result.coverUrl}
              alt={`Cover of ${result.title}`}
              className="w-16 h-24 object-cover rounded border border-lsc-border dark:border-earth-700"
            />
          </div>
        )}

        {/* Title and Basic Info */}
        <div className="flex-1 min-w-0">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream line-clamp-2" title={result.title}>
            {result.title}
          </h3>

          {/* Author */}
          {result.author && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              by <span className="font-medium">{result.author}</span>
            </p>
          )}

          {/* Item Type Badge */}
          <div className="flex items-center gap-2 mt-2">
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light">
              <BookOpen className="w-3 h-3" aria-hidden="true" />
              {result.itemType}
            </span>

            {/* Availability */}
            {result.availability && (
              <span
                className={clsx(
                  'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                  result.availability === 'available'
                    ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300'
                    : result.availability === 'checked-out'
                      ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300'
                      : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
                )}
                aria-label={`Availability: ${result.availability}`}
              >
                {result.availability === 'available' && '✓ Available'}
                {result.availability === 'checked-out' && '✗ Checked Out'}
                {result.availability === 'unknown' && '? Unknown'}
              </span>
            )}
          </div>
        </div>

        {/* Right Column: Rating & Score */}
        <div className="flex-shrink-0 text-right">
          {/* Relevance Score */}
          <div className="text-sm">
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Match</div>
            <div className="text-lg font-bold text-lsc-rose dark:text-lsc-rose-light">
              {result.relevanceScore}%
            </div>
          </div>

          {/* Rating */}
          {result.rating && (
            <div className="mt-2">
              <div className="flex items-center justify-end gap-1">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className={clsx(
                      'w-3.5 h-3.5',
                      i < Math.round(result.rating!)
                        ? 'text-status-warning-400 fill-yellow-400 dark:text-status-warning-300 dark:fill-yellow-300'
                        : 'text-earth-300 dark:text-earth-300'
                    )}
                    aria-hidden="true"
                  />
                ))}
              </div>
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                {result.rating.toFixed(1)}/5
              </div>
              {result.ratingCount && (
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  ({result.ratingCount.toLocaleString()})
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Description */}
      {result.description && (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2 mb-3" title={result.description}>
          {result.description}
        </p>
      )}

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-3 mb-3 text-sm">
        {result.publisher && (
          <div>
            <span className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Publisher</span>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{result.publisher}</p>
          </div>
        )}
        {result.year && (
          <div>
            <span className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Published</span>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{result.year}</p>
          </div>
        )}
        {result.pageCount && (
          <div>
            <span className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Pages</span>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{result.pageCount}</p>
          </div>
        )}
        {result.language && (
          <div>
            <span className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Language</span>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {result.language.map(formatLanguage).join(', ')}
            </p>
          </div>
        )}
      </div>

      {/* Subject Tags */}
      {result.subjects && result.subjects.length > 0 && (
        <div className="mb-3">
          <div className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-1.5">Topics</div>
          <div className="flex flex-wrap gap-1">
            {result.subjects.slice(0, 5).map((subject, index) => (
              <span
                key={index}
                className="inline-block px-2 py-1 rounded-full text-xs bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
              >
                {subject}
              </span>
            ))}
            {result.subjects.length > 5 && (
              <span className="inline-block px-2 py-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                +{result.subjects.length - 5} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* ISBN */}
      {result.isbn && (
        <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          ISBN: <code className="bg-earth-100 dark:bg-earth-700 px-1 rounded">{result.isbn}</code>
        </div>
      )}

      {/* Deduplication Indicator */}
      {showDeduplication && result.deduplication.merged && (
        <div className="mb-3 py-2 border-t border-lsc-border dark:border-earth-700">
          <DeduplicationIndicator dedup={result.deduplication} showDetails={false} />
        </div>
      )}

      {/* Source Attribution */}
      {showAttribution && (
        <div className="pt-3 border-t border-lsc-border dark:border-earth-700">
          <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Source</p>
          <SourceAttribution attributions={result.attribution} showMetadata={false} />
        </div>
      )}
    </article>
  )
}

// ==================== Utility Functions ====================

function formatLanguage(code: string): string {
  const languages: Record<string, string> = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'ja': 'Japanese',
    'zh': 'Chinese',
    'pt': 'Portuguese',
    'ru': 'Russian',
  }
  return languages[code.toLowerCase()] || code.toUpperCase()
}

export default ResultCard
