/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Continue Reading Rail (indie landing, logged-in only)
 * Up to 3 active indie borrows with reading-progress bars.
 */

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { BookOpen, ChevronRight } from 'lucide-react'
import {
  getActiveBorrows,
  generateSlug,
  type EbookBorrow,
} from '@/api/indie-catalog-api'
import { getActiveReadingProgress } from '@/api/indie-engagement-api'
import ReadingProgressBar from '@/components/indie/ReadingProgressBar'

const MAX_ITEMS = 3

export default function ContinueReadingRail(): React.ReactElement | null {
  const { data: borrows } = useQuery({
    queryKey: ['indie-active-borrows-landing'],
    queryFn: getActiveBorrows,
    staleTime: 60_000,
  })

  const { data: progressData } = useQuery({
    queryKey: ['indie-reading-progress-landing'],
    queryFn: getActiveReadingProgress,
    staleTime: 60_000,
  })

  if (!borrows || borrows.length === 0) return null

  const progressByEbookId = new Map(
    (progressData ?? []).map((p) => [p.ebook_id, p.percent]),
  )

  // Most-recently-borrowed first; sort by borrowed_at desc.
  const sorted = [...borrows].sort(
    (a: EbookBorrow, b: EbookBorrow) =>
      new Date(b.borrowed_at).getTime() - new Date(a.borrowed_at).getTime(),
  )
  const visible = sorted.slice(0, MAX_ITEMS)

  return (
    <section aria-label="Continue reading">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          Pick up where you left off
        </h2>
        <Link
          to="/indie/my-borrows"
          className="flex items-center gap-1 text-sm text-lsc-rose hover:underline"
        >
          All borrows <ChevronRight className="w-4 h-4" aria-hidden="true" />
        </Link>
      </div>
      <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" role="list">
        {visible.map((borrow) => {
          const percent = progressByEbookId.get(borrow.indie_ebook_id ?? borrow.ebook_id) ?? 0
          return (
            <li key={borrow.id}>
              <Link
                to={`/indie/book/${generateSlug(borrow.ebook_title, borrow.ebook_id)}`}
                className="flex gap-3 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-3 hover:shadow-md transition-shadow"
                aria-label={`Continue reading ${borrow.ebook_title} by ${borrow.author_pen_name}`}
              >
                <div className="w-14 h-20 bg-lsc-cream dark:bg-earth-700 rounded flex items-center justify-center flex-shrink-0 overflow-hidden">
                  {borrow.ebook_cover_url ? (
                    <img
                      src={borrow.ebook_cover_url}
                      alt={`Cover of ${borrow.ebook_title}`}
                      className="w-full h-full object-cover"
                      loading="lazy"
                      decoding="async"
                    />
                  ) : (
                    <BookOpen className="w-6 h-6 text-lsc-dark/30 dark:text-lsc-cream/30" aria-hidden="true" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <h3
                    className="font-serif font-semibold text-sm text-lsc-dark dark:text-lsc-cream line-clamp-2"
                    title={borrow.ebook_title}
                  >
                    {borrow.ebook_title}
                  </h3>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5 line-clamp-1">
                    by {borrow.author_pen_name}
                  </p>
                  {percent > 0 ? (
                    <ReadingProgressBar percent={percent} className="mt-2" />
                  ) : (
                    <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-2">
                      Open to start
                    </p>
                  )}
                </div>
              </Link>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
