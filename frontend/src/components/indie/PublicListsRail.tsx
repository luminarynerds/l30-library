/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Public Reading Lists Rail (indie landing)
 * Surfaces lists patrons have made public.
 */

import { Link } from 'react-router-dom'
import { ListChecks, ChevronRight, BookOpen } from 'lucide-react'
import type { PublicReadingList } from '@/api/indie-catalog-api'

export default function PublicListsRail({
  lists,
}: {
  lists: PublicReadingList[]
}): React.ReactElement | null {
  if (!lists || lists.length === 0) return null

  return (
    <section aria-label="Public reading lists">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <ListChecks className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          Lists patrons made
        </h2>
        <Link
          to="/indie/lists"
          className="flex items-center gap-1 text-sm text-lsc-rose hover:underline"
        >
          All lists <ChevronRight className="w-4 h-4" aria-hidden="true" />
        </Link>
      </div>
      <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" role="list">
        {lists.map((list) => (
          <li key={list.id}>
            <Link
              to={
                list.share_token
                  ? `/indie/lists/shared/${list.share_token}`
                  : '/indie/lists'
              }
              className="block bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4 hover:shadow-md transition-shadow"
              aria-label={`Reading list: ${list.name}, ${list.item_count} ${list.item_count === 1 ? 'book' : 'books'}`}
            >
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream line-clamp-2">
                {list.name}
              </h3>
              {list.description && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 line-clamp-2">
                  {list.description}
                </p>
              )}
              <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-2 flex items-center gap-1">
                <BookOpen className="w-3 h-3" aria-hidden="true" />
                {list.item_count} {list.item_count === 1 ? 'book' : 'books'}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
