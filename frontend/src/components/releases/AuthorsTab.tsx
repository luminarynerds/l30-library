/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Search,
  Users,
  User,
  RefreshCw,
  ExternalLink,
  Loader2,
} from 'lucide-react'
import type { Author } from '../../api/releases-api'
import { useTranslation } from '@/i18n'

interface AuthorsTabProps {
  authors: Author[]
  authorsTotal: number
  authorsPage: number
  authorSearch: string
  activeOnly: boolean
  refreshingAuthorId: string | null
  isLoading: boolean
  onAuthorSearch: (v: string) => void
  onActiveOnly: (v: boolean) => void
  onRefreshAuthor: (id: string) => void
  onPageChange: (p: number) => void
}

export function AuthorsTab({
  authors,
  authorsTotal,
  authorsPage,
  authorSearch,
  activeOnly,
  refreshingAuthorId,
  isLoading,
  onAuthorSearch,
  onActiveOnly,
  onRefreshAuthor,
  onPageChange,
}: AuthorsTabProps): React.ReactElement {
  const { t } = useTranslation()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
      </div>
    )
  }

  return (
    <div>
      {/* Search/Filter */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 mb-6 border border-lsc-border dark:border-earth-700">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" />
            <input
              type="text"
              placeholder={t('placeholder.releasesManagement.searchAuthors')}
              aria-label={t('aria.indieAuthorBrowse.searchAuthors')}
              value={authorSearch}
              onChange={(e) => onAuthorSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
            <input
              type="checkbox"
              checked={activeOnly}
              onChange={(e) => onActiveOnly(e.target.checked)}
              className="rounded border-lsc-border"
            />
            Active authors only
          </label>
        </div>
      </div>

      {/* Authors Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {authors.length === 0 ? (
          <div className="col-span-full bg-lsc-white dark:bg-earth-800 rounded-xl p-12 text-center border border-lsc-border dark:border-earth-700">
            <User className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No authors found</p>
          </div>
        ) : (
          authors.map((author) => (
            <div
              key={author.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700"
            >
              <div className="flex items-start gap-4">
                {author.image_url ? (
                  <img
                    src={author.image_url}
                    alt={author.name}
                    className="w-16 h-16 rounded-full object-cover"
                  />
                ) : (
                  <div className="w-16 h-16 rounded-full bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center">
                    <User className="w-8 h-8 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={author.name}>
                    {author.name}
                  </h3>
                  <div className="flex items-center gap-3 mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span className="flex items-center gap-1">
                      <Users className="w-3 h-3" />
                      {author.follower_count} followers
                    </span>
                    {!author.is_active && (
                      <span className="px-2 py-0.5 text-xs bg-earth-100 dark:bg-earth-700 rounded">
                        Inactive
                      </span>
                    )}
                  </div>
                  {author.website && (
                    <a
                      href={author.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-lsc-rose hover:underline flex items-center gap-1 mt-1"
                    >
                      <ExternalLink className="w-3 h-3" />
                      Website
                    </a>
                  )}
                </div>
              </div>
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => onRefreshAuthor(author.id)}
                  disabled={refreshingAuthorId === author.id}
                  className="flex-1 px-3 py-2 text-sm bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {refreshingAuthorId === author.id ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  Refresh Books
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Authors Pagination */}
      {authorsTotal > 25 && (
        <div className="mt-6 flex items-center justify-between">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Showing {(authorsPage - 1) * 25 + 1} to {Math.min(authorsPage * 25, authorsTotal)} of{' '}
            {authorsTotal}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(Math.max(1, authorsPage - 1))}
              disabled={authorsPage === 1}
              className="px-3 py-1 rounded-lg border border-lsc-border dark:border-earth-700 text-sm disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => onPageChange(authorsPage + 1)}
              disabled={authorsPage * 25 >= authorsTotal}
              className="px-3 py-1 rounded-lg border border-lsc-border dark:border-earth-700 text-sm disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
