/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { RefreshCw, ShoppingCart } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { DateRange } from "./types"

interface Props {
  libraryStatusFilter: string
  onLibraryStatusChange: (v: string) => void
  sourceFilter: string
  onSourceChange: (v: string) => void
  ageFilter: string
  onAgeChange: (v: string) => void
  dateRange: DateRange
  onDateRangeChange: (v: DateRange) => void
  onRefresh: () => void
  isRefreshing: boolean
  selectedCount: number
  onCreatePO: () => void
}

export default function ReleasesToolbar({
  libraryStatusFilter,
  onLibraryStatusChange,
  sourceFilter,
  onSourceChange,
  ageFilter,
  onAgeChange,
  dateRange,
  onDateRangeChange,
  onRefresh,
  isRefreshing,
  selectedCount,
  onCreatePO,
}: Props) {
  const { t } = useTranslation()
  const selectClass =
    "px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm"

  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        value={libraryStatusFilter}
        onChange={(e) => onLibraryStatusChange(e.target.value)}
        aria-label={t('components.acquisition.acquisitionReleasesTab.filterByLibraryStatus')}
        className={selectClass}
      >
        <option value="">All Status</option>
        <option value="new">{t('components.acquisition.acquisitionReleasesTab.newNotInLibrary')}</option>
        <option value="owned">Already Owned</option>
        <option value="on_order">On Order</option>
      </select>

      <select
        value={sourceFilter}
        onChange={(e) => onSourceChange(e.target.value)}
        aria-label={t('components.acquisition.acquisitionReleasesTab.filterBySource')}
        className={selectClass}
      >
        <option value="">All sources</option>
        <option value="author_scan">Followed authors</option>
        <option value="libraryreads">LibraryReads</option>
        <option value="lj_prepub">LJ Prepub Alert</option>
        <option value="editorial_rss">Editorial feed</option>
        <option value="indie_mastodon">Indie: Mastodon buzz</option>
        <option value="indie_itchio">Indie: itch.io</option>
      </select>

      <select
        value={ageFilter}
        onChange={(e) => onAgeChange(e.target.value)}
        aria-label={t('components.acquisition.acquisitionReleasesTab.filterByAgeRating')}
        className={selectClass}
      >
        <option value="">All Ages</option>
        <option value="child">Children</option>
        <option value="teen">Teen</option>
        <option value="adult">Adult</option>
      </select>

      <select
        value={dateRange}
        onChange={(e) => onDateRangeChange(e.target.value as DateRange)}
        aria-label={t('components.acquisition.acquisitionReleasesTab.filterByDateRange')}
        className={selectClass}
      >
        <option value="all">All Dates</option>
        <option value="this_week">This Week</option>
        <option value="this_month">This Month</option>
        <option value="next_3_months">Next 3 Months</option>
        <option value="past">Already Released</option>
      </select>

      <div className="flex-1" />

      <button
        onClick={onRefresh}
        disabled={isRefreshing}
        className="flex items-center gap-2 px-3 py-2 bg-lsc-cream hover:bg-lsc-cream/80 dark:bg-lsc-brown dark:hover:bg-lsc-brown/90 text-lsc-dark dark:text-earth-300 rounded-xl text-sm font-medium"
      >
        <RefreshCw aria-hidden="true" className={"w-4 h-4 " + (isRefreshing ? "motion-safe:animate-spin" : "")} />
        Refresh
      </button>

      {selectedCount > 0 && (
        <button
          onClick={onCreatePO}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"
        >
          <ShoppingCart aria-hidden="true" className="w-4 h-4" />
          Create PO ({selectedCount})
        </button>
      )}
    </div>
  )
}
