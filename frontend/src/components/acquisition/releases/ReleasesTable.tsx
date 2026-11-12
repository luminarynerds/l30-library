/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ArrowUpDown, BookOpen, Calendar, ChevronLeft, ChevronRight, RefreshCw, Star, TrendingUp } from "lucide-react"
import { useTranslation } from "@/i18n"
import { daysUntil, formatReleaseDate, getAgeBadgeClass, getStatusBadgeClass } from "./utils"
import type { LibrarianRelease, SortDir, SortField } from "./types"

const SOURCE_LABELS: Record<string, string> = {
  author_scan: "Followed authors",
  libraryreads: "LibraryReads",
  lj_prepub: "LJ Prepub",
  editorial_rss: "Editorial",
  indie_mastodon: "Indie (Mastodon)",
  indie_itchio: "Indie (itch.io)",
}

function sourceLabel(source: string): string {
  return SOURCE_LABELS[source] || source
}

interface Props {
  releases: LibrarianRelease[]
  isLoading: boolean
  selectedReleases: string[]
  onToggleSelect: (id: string, checked: boolean) => void
  onSelectAll: () => void
  allSelectableSelected: boolean
  onRowClick: (r: LibrarianRelease) => void
  sortField: SortField
  sortDir: SortDir
  onToggleSort: (field: SortField) => void
  formatMoney: (n: number) => string
  page: number
  perPage: number
  total: number
  totalPages: number
  onPageChange: (p: number | ((prev: number) => number)) => void
}

export default function ReleasesTable({
  releases,
  isLoading,
  selectedReleases,
  onToggleSelect,
  onSelectAll,
  allSelectableSelected,
  onRowClick,
  sortField,
  sortDir: _sortDir,
  onToggleSort,
  formatMoney,
  page,
  perPage,
  total,
  totalPages,
  onPageChange,
}: Props) {
  const { t } = useTranslation()

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <RefreshCw className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (releases.length === 0) {
    return (
      <div className="text-center py-12">
        <Calendar aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">
          {t('components.acquisition.acquisitionReleasesTab.noUpcomingReleasesFound')}
        </p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
          Follow authors in the Release Radar to track their upcoming books, then refresh here.
        </p>
      </div>
    )
  }

  const SortHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <button
      onClick={() => onToggleSort(field)}
      className="flex items-center gap-1 text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase hover:text-lsc-rose"
    >
      {children}
      <ArrowUpDown className={"w-3 h-3 " + (sortField === field ? "text-lsc-rose" : "opacity-40")} />
    </button>
  )

  return (
    <>
      <div className="overflow-x-auto border border-lsc-border dark:border-earth-700 rounded-xl">
        <table className="w-full">
          <thead className="bg-lsc-cream dark:bg-lsc-brown/50">
            <tr>
              <th className="w-10 px-4 py-3">
                <input
                  type="checkbox"
                  checked={allSelectableSelected}
                  onChange={onSelectAll}
                  className="w-4 h-4 rounded border-lsc-border text-lsc-rose"
                  aria-label={t('components.acquisition.acquisitionReleasesTab.selectAllNewReleases')}
                  title={t('components.acquisition.acquisitionReleasesTab.selectAllNewReleases2')}
                />
              </th>
              <th className="px-4 py-3 text-left">
                <SortHeader field="release_date">Release</SortHeader>
              </th>
              <th className="px-4 py-3 text-left">
                <SortHeader field="title">Title / Author</SortHeader>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                ISBN
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                Age
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                Source
              </th>
              <th className="px-4 py-3 text-center">
                <SortHeader field="demand">Demand</SortHeader>
              </th>
              <th className="px-4 py-3 text-right">
                <SortHeader field="price">Price</SortHeader>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
            {releases.map((release) => {
              const days = daysUntil(release.book.release_date)
              const isUrgent = days !== null && days >= 0 && days <= 7
              return (
                <tr
                  key={release.book.id}
                  className={"hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/30 cursor-pointer " + (isUrgent ? "bg-status-warning-50/50 dark:bg-status-warning-900/10" : "")}
                  onClick={() => onRowClick(release)}
                >
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedReleases.includes(release.book.id)}
                      onChange={(e) => onToggleSelect(release.book.id, e.target.checked)}
                      disabled={release.library_status !== "new"}
                      className="w-4 h-4 rounded border-lsc-border text-lsc-rose disabled:opacity-50"
                    />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {formatReleaseDate(release.book.release_date, release.book.is_date_exact)}
                    </div>
                    {days !== null && days >= 0 && (
                      <div className={"text-xs mt-0.5 " + (isUrgent ? "text-lsc-rose font-medium" : "text-lsc-dark/70 dark:text-lsc-cream/60")}>
                        {days === 0 ? "Today" : days === 1 ? "Tomorrow" : `${days} days`}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {release.book.cover_url ? (
                        <img
                          src={release.book.cover_url}
                          alt=""
                          className="w-8 h-12 object-cover rounded shadow-sm flex-shrink-0"
                        />
                      ) : (
                        <div className="w-8 h-12 bg-lsc-cream dark:bg-lsc-brown rounded flex items-center justify-center flex-shrink-0">
                          <BookOpen className="w-4 h-4 text-lsc-dark/30 dark:text-lsc-cream/60" />
                        </div>
                      )}
                      <div className="min-w-0">
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate max-w-xs flex items-center gap-1" title={release.book.title}>
                          {release.book.is_featured && (
                            <Star aria-label="Featured" className="w-3.5 h-3.5 text-lsc-rose fill-lsc-rose flex-shrink-0" />
                          )}
                          <span className="truncate">{release.book.title}</span>
                        </p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 truncate" title={release.author_name}>
                          {release.author_name}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {release.book.isbn_13 || "-"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={"px-2 py-0.5 text-xs font-medium rounded capitalize " + getAgeBadgeClass(release.book.age_rating)}>
                      {release.book.age_rating || "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={"px-2 py-0.5 text-xs font-medium rounded " + getStatusBadgeClass(release.library_status)}>
                      {release.library_status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">
                    {sourceLabel(release.book.source)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {release.demand_score > 0 ? (
                      <span className="inline-flex items-center gap-1 text-sm font-medium text-lsc-rose">
                        <TrendingUp aria-hidden="true" className="w-3 h-3" />
                        {release.demand_score}
                      </span>
                    ) : (
                      <span className="text-lsc-dark/70 dark:text-lsc-cream/60">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {release.book.list_price ? formatMoney(release.book.list_price) : "-"}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
            Showing {(page - 1) * perPage + 1}-{Math.min(page * perPage, total)} of {total} releases
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-xl border border-lsc-border dark:border-earth-700 disabled:opacity-30 hover:bg-lsc-cream dark:hover:bg-lsc-brown"
              aria-label={t('aria.account.previousPage')}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream px-2">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => onPageChange((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-2 rounded-xl border border-lsc-border dark:border-earth-700 disabled:opacity-30 hover:bg-lsc-cream dark:hover:bg-lsc-brown"
              aria-label={t('aria.account.nextPage')}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </>
  )
}
