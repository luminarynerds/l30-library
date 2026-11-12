/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Gem, Star } from 'lucide-react'
import { type HiddenGemResult } from '@/api/domains/catalog/semantic-search-api'
import { SourceBadge } from './SearchResultCard'

export function HiddenGemCard({ gem }: { gem: HiddenGemResult }) {
  const gemPct = Math.round(gem.gem_score * 100)
  const similarityPct = Math.round(gem.avg_similarity_to_popular * 100)

  return (
    <div className="border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4 bg-gradient-to-br from-status-warning-50 to-orange-50 dark:from-status-warning-900/10 dark:to-orange-900/10">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Gem className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0" />
            <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={gem.title}>
              {gem.title}
            </h3>
          </div>
          {gem.author && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{gem.author}</p>
          )}

          <p className="text-xs text-status-warning-700 dark:text-status-warning-300 mb-2">
            {similarityPct}% similar to popular books in this genre — but only {gem.circulation_count} checkouts.
            This is a hidden gem waiting to be discovered!
          </p>

          {gem.subjects && gem.subjects.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {gem.subjects.slice(0, 4).map((s, i) => (
                <span
                  key={i}
                  className="px-1.5 py-0.5 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 text-xs rounded"
                >
                  {s}
                </span>
              ))}
            </div>
          )}

          <div className="flex items-center gap-2 mt-2">
            <SourceBadge source={gem.source_collection} />
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{gem.circulation_count} checkouts</span>
          </div>
        </div>

        <div className="flex-shrink-0 text-center bg-status-warning-100 dark:bg-status-warning-900/30 rounded-lg p-3 min-w-[60px]">
          <div className="text-xl font-bold text-status-warning-700 dark:text-status-warning-300 tabular-nums">
            {gemPct}
          </div>
          <div className="text-xs text-status-warning-600 dark:text-status-warning-400 whitespace-nowrap">gem score</div>
          <Star className="w-3 h-3 text-status-warning-500 mx-auto mt-1" />
        </div>
      </div>
    </div>
  )
}
