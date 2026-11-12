/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SuggestionsSkeleton Component
 *
 * Skeleton loading state for autocomplete suggestions.
 * Shows animated placeholders while suggestions are being fetched.
 */

import React from 'react'
import Skeleton from '@/components/Skeleton'
import { t } from '@/i18n'

interface SuggestionsSkeletonProps {
  /** Number of skeleton items to show */
  count?: number
}

export function SuggestionsSkeleton({
  count = 4,
}: SuggestionsSkeletonProps): React.ReactElement {
  // Vary widths for natural appearance
  const widths = ['w-3/4', 'w-2/3', 'w-4/5', 'w-1/2', 'w-3/5']

  return (
    <div className="p-2 space-y-1" role="status" aria-label={t('aria.federated-search.loadingSuggestions')}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 px-4 py-2"
        >
          {/* Search icon placeholder */}
          <Skeleton className="w-3 h-3 rounded flex-shrink-0" />
          {/* Text placeholder with varying width */}
          <Skeleton className={`h-4 ${widths[i % widths.length]}`} />
        </div>
      ))}
    </div>
  )
}

export default SuggestionsSkeleton
