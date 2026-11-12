/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Download, Filter, Rss, Search, X } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { US_STATES_MAP, SOURCE_LABELS, formatReason } from './ban-tracker-data'
import type { StateCount, TypeCount, ReasonCount } from './types'

function buildExportUrl(
  ext: 'csv' | 'rss',
  state: string,
  banType: string,
  reason: string,
  source: string,
  search: string,
): string {
  const params = new URLSearchParams()
  if (state) params.set('state', state)
  if (banType) params.set('ban_type', banType)
  if (reason) params.set('reason_category', reason)
  if (source) params.set('source', source)
  if (search) params.set('search', search)
  const qs = params.toString()
  const base = `/api/v1/ban-tracker/public/reports.${ext}`
  return qs ? `${base}?${qs}` : base
}

export function FilterBar({
  states,
  banTypes,
  reasonCategories,
  selectedState,
  selectedBanType,
  selectedReason,
  selectedSource,
  searchQuery,
  onStateChange,
  onBanTypeChange,
  onReasonChange,
  onSourceChange,
  onSearchChange,
  onClearFilters,
  hasActiveFilters,
}: {
  states: StateCount[]
  banTypes: TypeCount[]
  reasonCategories: ReasonCount[]
  selectedState: string
  selectedBanType: string
  selectedReason: string
  selectedSource: string
  searchQuery: string
  onStateChange: (val: string) => void
  onBanTypeChange: (val: string) => void
  onReasonChange: (val: string) => void
  onSourceChange: (val: string) => void
  onSearchChange: (val: string) => void
  onClearFilters: () => void
  hasActiveFilters: boolean
}): React.ReactElement {
  const { t } = useTranslation()
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <Filter className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        <span className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Filters</span>
        {hasActiveFilters && (
          <button
            onClick={onClearFilters}
            className="ml-auto inline-flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
            aria-label={t('aria.catalog.clearAllFilters')}
          >
            <X className="w-3 h-3" aria-hidden="true" />
            Clear all
          </button>
        )}
        <div className={hasActiveFilters ? 'flex items-center gap-2' : 'ml-auto flex items-center gap-2'}>
          <a
            href={buildExportUrl('csv', selectedState, selectedBanType, selectedReason, selectedSource, searchQuery)}
            target="_blank"
            rel="noopener"
            download
            className="inline-flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
            aria-label="Export filtered reports as CSV"
          >
            <Download className="w-3 h-3" aria-hidden="true" />
            CSV
          </a>
          <a
            href={buildExportUrl('rss', selectedState, selectedBanType, selectedReason, selectedSource, searchQuery)}
            target="_blank"
            rel="noopener"
            className="inline-flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
            aria-label="Subscribe to filtered reports via RSS"
          >
            <Rss className="w-3 h-3" aria-hidden="true" />
            RSS
          </a>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {/* Search */}
        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60"
            aria-hidden="true"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={t('publicBanTracker.searchTitleOrAuthor')}
            className="w-full pl-9 pr-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-sm text-lsc-dark dark:text-lsc-cream placeholder-earth-400 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            aria-label={t('publicBanTracker.searchByTitleOrAuthor')}
          />
        </div>

        {/* State filter */}
        <select
          value={selectedState}
          onChange={(e) => onStateChange(e.target.value)}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          aria-label={t('aria.publicBanTracker.filterByState')}
        >
          <option value="">All States</option>
          {[...states]
            .sort((a, b) => a.state.localeCompare(b.state))
            .map((s) => (
              <option key={s.state} value={s.state}>
                {US_STATES_MAP[s.state] ?? s.state} ({s.count})
              </option>
            ))}
        </select>

        {/* Ban type filter */}
        <select
          value={selectedBanType}
          onChange={(e) => onBanTypeChange(e.target.value)}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          aria-label={t('publicBanTracker.filterByBanType')}
        >
          <option value="">All Types</option>
          {banTypes.map((t) => (
            <option key={t.ban_type} value={t.ban_type}>
              {t.ban_type.charAt(0) + t.ban_type.slice(1).toLowerCase()} ({t.count})
            </option>
          ))}
        </select>

        {/* Reason filter */}
        <select
          value={selectedReason}
          onChange={(e) => onReasonChange(e.target.value)}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          aria-label={t('publicBanTracker.filterByReasonCategory')}
        >
          <option value="">All Reasons</option>
          {[...reasonCategories]
            .sort((a, b) => a.reason_category.localeCompare(b.reason_category))
            .map((r) => (
              <option key={r.reason_category} value={r.reason_category}>
                {formatReason(r.reason_category)} ({r.count})
              </option>
            ))}
        </select>

        {/* Source filter */}
        <select
          value={selectedSource}
          onChange={(e) => onSourceChange(e.target.value)}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          aria-label={t('aria.publicBanTracker.filterBySource')}
        >
          <option value="">All Sources</option>
          {Object.entries(SOURCE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
