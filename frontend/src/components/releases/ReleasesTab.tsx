/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  BookOpen,
  Package,
  ShoppingCart,
  TrendingUp,
  Calendar,
  Users,
  Loader2,
} from 'lucide-react'
import type { LibrarianReleaseItem } from '../../api/releases-api'
import { useTranslation, getCurrentLocale } from '@/i18n'

interface ReleasesTabProps {
  releases: LibrarianReleaseItem[]
  releasesTotal: number
  releasesPage: number
  releaseStatusFilter: 'upcoming' | 'released' | ''
  libraryStatusFilter: 'new' | 'owned' | 'on_order' | ''
  ageRatingFilter: 'child' | 'teen' | 'adult' | ''
  minDemandFilter: number
  selectedReleases: Set<string>
  isLoading: boolean
  onReleaseStatusFilter: (v: 'upcoming' | 'released' | '') => void
  onLibraryStatusFilter: (v: 'new' | 'owned' | 'on_order' | '') => void
  onAgeRatingFilter: (v: 'child' | 'teen' | 'adult' | '') => void
  onMinDemandFilter: (v: number) => void
  onToggleRelease: (bookId: string) => void
  onSelectAll: () => void
  onPageChange: (p: number) => void
}

function getLibraryStatusBadge(status: string) {
  switch (status) {
    case 'new':
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400">
          New
        </span>
      )
    case 'owned':
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light">
          Owned
        </span>
      )
    case 'on_order':
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400">
          On Order
        </span>
      )
    default:
      return null
  }
}

function getAgeRatingBadge(rating: string) {
  switch (rating) {
    case 'child':
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-400">
          Children
        </span>
      )
    case 'teen':
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light">
          Teen
        </span>
      )
    case 'adult':
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-earth-100 text-earth-700 dark:bg-earth-700/30 dark:text-earth-300">
          Adult
        </span>
      )
    default:
      return null
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'TBD'
  return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function ReleasesTab({
  releases,
  releasesTotal,
  releasesPage,
  releaseStatusFilter,
  libraryStatusFilter,
  ageRatingFilter,
  minDemandFilter,
  selectedReleases,
  isLoading,
  onReleaseStatusFilter,
  onLibraryStatusFilter,
  onAgeRatingFilter,
  onMinDemandFilter,
  onToggleRelease,
  onSelectAll,
  onPageChange,
}: ReleasesTabProps): React.ReactElement {
  const { t } = useTranslation()
  const newReleasesCount = releases.filter((r) => r.library_status === 'new').length

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
      </div>
    )
  }

  return (
    <div>
      {/* Filters */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Release Status
            </label>
            <select
              value={releaseStatusFilter}
              onChange={(e) => onReleaseStatusFilter(e.target.value as typeof releaseStatusFilter)}
              className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            >
              <option value="">All</option>
              <option value="upcoming">Upcoming</option>
              <option value="released">Released</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Library Status
            </label>
            <select
              value={libraryStatusFilter}
              onChange={(e) => onLibraryStatusFilter(e.target.value as typeof libraryStatusFilter)}
              className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            >
              <option value="">All</option>
              <option value="new">{t('releasesManagement.newNotInLibrary')}</option>
              <option value="owned">Owned</option>
              <option value="on_order">On Order</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Age Rating
            </label>
            <select
              value={ageRatingFilter}
              onChange={(e) => onAgeRatingFilter(e.target.value as typeof ageRatingFilter)}
              className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            >
              <option value="">All</option>
              <option value="child">Children</option>
              <option value="teen">Teen</option>
              <option value="adult">Adult</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Min Demand Score
            </label>
            <input
              type="number"
              min="0"
              value={minDemandFilter}
              onChange={(e) => onMinDemandFilter(parseInt(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-lsc-cream dark:bg-lsc-brown rounded-lg">
              <BookOpen className="w-5 h-5 text-lsc-rose" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Releases</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{releasesTotal}</p>
            </div>
          </div>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-status-success-100 dark:bg-status-success-900/30 rounded-lg">
              <Package className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">New Titles</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{newReleasesCount}</p>
            </div>
          </div>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-earth-100 dark:bg-earth-800/30 rounded-lg">
              <ShoppingCart className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Selected</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{selectedReleases.size}</p>
            </div>
          </div>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-category-100 dark:bg-category-900/30 rounded-lg">
              <TrendingUp className="w-5 h-5 text-category-600 dark:text-category-400" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">High Demand</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">
                {releases.filter((r) => r.demand_score >= 5).length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Releases Table */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl overflow-hidden border border-lsc-border dark:border-earth-700">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-lsc-cream dark:bg-lsc-brown">
              <tr>
                <th className="px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectedReleases.size === newReleasesCount && newReleasesCount > 0}
                    onChange={onSelectAll}
                    className="rounded border-lsc-border"
                    aria-label={t('releasesManagement.selectAllNewReleases')}
                  />
                </th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Title
                </th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Author
                </th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Release Date
                </th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Library Status
                </th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Age
                </th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Demand
                </th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Price
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
              {releases.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center">
                    <BookOpen className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-3" />
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No releases found</p>
                  </td>
                </tr>
              ) : (
                releases.map((release) => (
                  <tr
                    key={release.book.id}
                    className="hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors"
                  >
                    <td className="px-4 py-3">
                      {release.library_status === 'new' && (
                        <input
                          type="checkbox"
                          checked={selectedReleases.has(release.book.id)}
                          onChange={() => onToggleRelease(release.book.id)}
                          className="rounded border-lsc-border"
                          aria-label={`Select ${release.book.title}`}
                        />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        {release.book.cover_url ? (
                          <img
                            src={release.book.cover_url}
                            alt={`Cover of ${release.book.title}`}
                            className="w-10 h-14 object-cover rounded shadow-sm"
                          />
                        ) : (
                          <div className="w-10 h-14 bg-lsc-cream dark:bg-lsc-brown rounded flex items-center justify-center">
                            <BookOpen className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" />
                          </div>
                        )}
                        <div>
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {release.book.title}
                          </p>
                          {release.book.isbn_13 && (
                            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                              {release.book.isbn_13}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {release.author_name}
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        {formatDate(release.book.release_date)}
                      </div>
                    </td>
                    <td className="px-4 py-3">{getLibraryStatusBadge(release.library_status)}</td>
                    <td className="px-4 py-3">{getAgeRatingBadge(release.book.age_rating)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                        <span
                          className={`font-medium ${
                            release.demand_score >= 5
                              ? 'text-lsc-rose'
                              : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                          }`}
                        >
                          {release.demand_score}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {release.book.list_price ? `$${release.book.list_price.toFixed(2)}` : '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {releasesTotal > 25 && (
          <div className="px-4 py-3 border-t border-lsc-border dark:border-earth-700 flex items-center justify-between">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Showing {(releasesPage - 1) * 25 + 1} to {Math.min(releasesPage * 25, releasesTotal)} of{' '}
              {releasesTotal}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => onPageChange(Math.max(1, releasesPage - 1))}
                disabled={releasesPage === 1}
                className="px-3 py-1 rounded-lg border border-lsc-border dark:border-earth-700 text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => onPageChange(releasesPage + 1)}
                disabled={releasesPage * 25 >= releasesTotal}
                className="px-3 py-1 rounded-lg border border-lsc-border dark:border-earth-700 text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
