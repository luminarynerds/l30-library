/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"
import { Search, Filter, Loader2 } from "lucide-react"
import { useTranslation} from '@/i18n'

type StatusFilter = "all" | "active" | "blocked"

interface PatronSearchBarProps {
  searchQuery: string
  onSearchQueryChange: (query: string) => void
  statusFilter: StatusFilter
  onStatusFilterChange: (filter: StatusFilter) => void
  isSearching: boolean
  onSearch: (e: React.FormEvent) => void
}

export function PatronSearchBar({
  searchQuery,
  onSearchQueryChange,
  statusFilter,
  onStatusFilterChange,
  isSearching,
  onSearch,
}: PatronSearchBarProps) {
  const { t } = useTranslation()
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
      <form onSubmit={onSearch} className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchQueryChange(e.target.value)}
            placeholder={t('components.staff.patronSearchBar.searchByNameEmailOr')}
            aria-label={t('components.staff.patronSearchBar.searchByNameEmailOr2')}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
        </div>
        <div className="flex gap-2">
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <select
              value={statusFilter}
              onChange={(e) => onStatusFilterChange(e.target.value as StatusFilter)}
              aria-label={t('aria.staff.filterPatronsByStatus')}
              className="pl-9 pr-8 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent appearance-none cursor-pointer"
            >
              <option value="all">All Patrons</option>
              <option value="active">Active Only</option>
              <option value="blocked">Blocked Only</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={isSearching}
            className="px-6 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose text-white rounded-xl font-medium flex items-center gap-2 transition-colors"
          >
            {isSearching ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Search aria-hidden="true" className="w-4 h-4" />}
            Search
          </button>
        </div>
      </form>
    </div>
  )
}
