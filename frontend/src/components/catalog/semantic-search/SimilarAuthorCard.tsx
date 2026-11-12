/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Users, Search } from 'lucide-react'
import { type SimilarAuthor } from '@/api/domains/catalog/semantic-search-api'
import { SimilarityBadge, SourceBadge } from './SearchResultCard'

export function SimilarAuthorCard({
  author,
  onSearch,
}: {
  author: SimilarAuthor
  onSearch?: (name: string) => void
}) {
  return (
    <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4 bg-lsc-white dark:bg-earth-800 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Users className="w-4 h-4 text-rose-500 flex-shrink-0" />
            <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
              {author.author_name}
            </h3>
          </div>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            {author.book_count} book{author.book_count !== 1 ? 's' : ''} in collection
          </p>

          {author.shared_subjects.length > 0 && (
            <div className="mb-2">
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Shared topics: </span>
              <span className="text-xs text-lsc-rose dark:text-lsc-rose-light">
                {author.shared_subjects.slice(0, 4).join(', ')}
              </span>
            </div>
          )}

          {author.genres.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {author.genres.slice(0, 3).map((g, i) => (
                <span
                  key={i}
                  className="px-1.5 py-0.5 bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-300 text-xs rounded border border-rose-100 dark:border-rose-800"
                >
                  {g}
                </span>
              ))}
            </div>
          )}

          {author.source_collections.length > 0 && (
            <div className="flex gap-1">
              {author.source_collections.map((s) => (
                <SourceBadge key={s} source={s} />
              ))}
            </div>
          )}
        </div>

        <div className="flex-shrink-0 flex flex-col items-end gap-2">
          <SimilarityBadge score={author.similarity_score} />
          {onSearch && (
            <button
              onClick={() => onSearch(author.author_name)}
              className="text-xs text-rose-700 dark:text-rose-400 hover:underline flex items-center gap-1"
            >
              <Search className="w-3 h-3" />
              Explore
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
