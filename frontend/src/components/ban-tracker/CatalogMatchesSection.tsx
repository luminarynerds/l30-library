/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Library, BookOpen, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { clean } from '@/lib/utils'
import { getBanTypeBadge, US_STATES_MAP } from './ban-tracker-data'
import type { BanReport } from './types'

export function CatalogMatchesSection({
  reports,
}: {
  reports: BanReport[]
}): React.ReactElement | null {
  const matched = reports.filter((r) => r.has_in_catalog)
  if (matched.length === 0) return null

  // Group reports by title+author to deduplicate books banned in multiple states
  const groupedMap = new Map<string, {
    title: string
    author: string
    cover_url?: string
    catalog_item_id?: number
    bans: Array<{ state: string; ban_type: string }>
  }>()

  for (const report of matched) {
    const key = `${report.title}|||${report.author}`
    const existing = groupedMap.get(key)
    if (existing) {
      existing.bans.push({ state: report.state, ban_type: report.ban_type })
    } else {
      groupedMap.set(key, clean({
        title: report.title,
        author: report.author,
        cover_url: report.cover_url,
        catalog_item_id: report.catalog_item_id,
        bans: [{ state: report.state, ban_type: report.ban_type }],
      }))
    }
  }

  const groupedBooks = Array.from(groupedMap.values())

  return (
    <section aria-labelledby="catalog-matches-heading">
      <div className="flex items-center gap-2 mb-4">
        <Library className="w-5 h-5 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
        <h2
          id="catalog-matches-heading"
          className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream"
        >
          In Our Collection
        </h2>
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
          ({groupedBooks.length} book{groupedBooks.length !== 1 ? 's' : ''})
        </span>
      </div>

      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        These books have been banned or challenged elsewhere but remain freely available in our
        catalog. We believe in the freedom to read.
      </p>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {groupedBooks.map((book) => (
          <div
            key={`${book.title}|||${book.author}`}
            className="bg-status-success-50 dark:bg-status-success-900/10 rounded-xl border border-status-success-200 dark:border-status-success-800/30 p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start gap-3">
              {book.cover_url ? (
                <img
                  src={book.cover_url}
                  alt={`Cover of ${book.title}`}
                  className="w-12 h-[72px] rounded object-cover flex-shrink-0 shadow-sm"
                  loading="lazy"
                  onError={(e) => { e.currentTarget.style.display = 'none'; e.currentTarget.nextElementSibling?.classList.remove('hidden') }}
                />
              ) : null}
              <div className={`w-9 h-9 rounded-lg bg-status-success-100 dark:bg-status-success-900/30 flex items-center justify-center flex-shrink-0 ${book.cover_url ? 'hidden' : ''}`}>
                <BookOpen className="w-4 h-4 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="font-bold text-sm text-lsc-dark dark:text-lsc-cream leading-tight truncate" title={book.title}>
                  {book.title}
                </h4>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">
                  {book.author}
                </p>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {book.bans.map((ban) => {
                    const badge = getBanTypeBadge(ban.ban_type)
                    return (
                      <span
                        key={`${ban.state}-${ban.ban_type}`}
                        className={`px-2 py-0.5 text-[10px] font-semibold rounded-full ${badge.className}`}
                      >
                        {badge.label} in {US_STATES_MAP[ban.state] ?? ban.state}
                      </span>
                    )
                  })}
                </div>
                {book.catalog_item_id && (
                  <Link
                    to={`/catalog/${book.catalog_item_id}`}
                    className="inline-flex items-center gap-1 text-xs text-lsc-rose dark:text-lsc-rose-light hover:underline mt-2 font-medium"
                  >
                    View in catalog
                    <ChevronRight className="w-3 h-3" aria-hidden="true" />
                  </Link>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
