/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Flame, Hash, MapPin } from 'lucide-react'
import type { MostBannedBook } from './types'

function getRankStyle(rank: number): string {
  switch (rank) {
    case 1:
      return 'bg-status-warning-400 dark:bg-status-warning-500 text-white'
    case 2:
      return 'bg-earth-300 dark:bg-earth-500 text-white'
    case 3:
      return 'bg-status-warning-600 dark:bg-status-warning-700 text-white'
    default:
      return 'bg-earth-200 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
  }
}

export function MostChallengedSection({
  books,
}: {
  books: MostBannedBook[]
}): React.ReactElement | null {
  if (books.length === 0) return null

  return (
    <section aria-labelledby="most-challenged-heading">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
        <div className="flex items-center gap-2 mb-5">
          <Flame className="w-5 h-5 text-status-danger-500 dark:text-status-danger-400" aria-hidden="true" />
          <h2
            id="most-challenged-heading"
            className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream"
          >
            Most Challenged Books
          </h2>
        </div>

        <div className="space-y-2">
          {books.map((book, index) => {
            const rank = index + 1
            return (
              <div
                key={`${book.title}-${book.author}`}
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-700/50 transition-colors"
              >
                {/* Rank badge */}
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${getRankStyle(rank)}`}
                  aria-label={`Rank ${rank}`}
                >
                  {rank}
                </div>

                {/* Book info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-1.5 flex-wrap">
                    <span className="font-bold text-sm text-lsc-dark dark:text-lsc-cream truncate" title={book.title}>
                      {book.title}
                    </span>
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                      — {book.author}
                    </span>
                  </div>
                </div>

                {/* Stats */}
                <div className="flex items-center gap-3 flex-shrink-0">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300">
                    <Hash className="w-3 h-3" aria-hidden="true" />
                    {book.report_count} {book.report_count === 1 ? 'report' : 'reports'}
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                    <MapPin className="w-3 h-3" aria-hidden="true" />
                    {book.state_count} {book.state_count === 1 ? 'state' : 'states'}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
