/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef } from "react"
import { Search, Filter, Loader2, ChevronDown, ChevronUp, X } from "lucide-react"
import { useAdaptiveDebounce } from "../../../../hooks/useAdaptiveDebounce"
import type { StatusFilter } from "../types"
import type { PatronAdvancedFilters, OverdueFilter, CardStatusFilter } from "@/api/staff-api/patrons"
import { useTranslation} from '@/i18n'

interface PatronSearchPanelProps {
  searchQuery: string
  onSearchQueryChange: (query: string) => void
  statusFilter: StatusFilter
  onStatusFilterChange: (filter: StatusFilter) => void
  onSearch: (e: React.FormEvent) => void
  isSearching: boolean
  onPageChange?: (page: number) => void
  onDebouncedSearch?: (query: string) => void
  advancedFilters: PatronAdvancedFilters
  onAdvancedFiltersChange: (filters: PatronAdvancedFilters) => void
  onClearAdvancedFilters: () => void
  activeFilterCount: number
}

export function PatronSearchPanel({
  searchQuery,
  onSearchQueryChange,
  statusFilter,
  onStatusFilterChange,
  onSearch,
  isSearching,
  onPageChange,
  onDebouncedSearch,
  advancedFilters,
  onAdvancedFiltersChange,
  onClearAdvancedFilters,
  activeFilterCount,
}: PatronSearchPanelProps) {
  const { t } = useTranslation()
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false)
  const hasTriggeredInitialDebounceRef = useRef(false)
  const onDebouncedSearchRef = useRef(onDebouncedSearch)

  useEffect(() => {
    onDebouncedSearchRef.current = onDebouncedSearch
  }, [onDebouncedSearch])

  // Debounced live search: triggers API call as user types
  const debouncedQuery = useAdaptiveDebounce(searchQuery)

  useEffect(() => {
    if (!hasTriggeredInitialDebounceRef.current) {
      hasTriggeredInitialDebounceRef.current = true
      return
    }

    if (onDebouncedSearchRef.current) {
      onDebouncedSearchRef.current(debouncedQuery)
    }
  }, [debouncedQuery])

  const updateFilter = <K extends keyof PatronAdvancedFilters>(
    key: K,
    value: PatronAdvancedFilters[K] | undefined
  ) => {
    const next = { ...advancedFilters }
    if (value === undefined || value === "") {
      delete next[key]
    } else {
      next[key] = value
    }
    onAdvancedFiltersChange(next)
    onPageChange?.(1)
  }

  const inputClasses =
    "w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
  const labelClasses =
    "block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
      <form onSubmit={onSearch} className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchQueryChange(e.target.value)}
            placeholder={t('patronSearchPanel.searchByNameEmailOr')}
            aria-label={t('aria.homeDeliveryManagement.searchPatrons')}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
          {isSearching && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
          )}
        </div>
        <div className="flex gap-2">
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <select
              value={statusFilter}
              onChange={(e) => {
                onStatusFilterChange(e.target.value as StatusFilter)
                onPageChange?.(1)
              }}
              aria-label={t('patronSearchPanel.filterByPatronStatus')}
              className="pl-9 pr-8 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent appearance-none cursor-pointer"
            >
              <option value="all">{t('patronSearchPanel.allPatrons')}</option>
              <option value="active">{t('patronSearchPanel.activeOnly')}</option>
              <option value="blocked">{t('patronSearchPanel.blockedOnly')}</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={isSearching}
            className="px-6 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose text-white rounded-xl font-medium flex items-center gap-2 transition-colors"
          >
            {isSearching ? (
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
            ) : (
              <Search aria-hidden="true" className="w-4 h-4" />
            )}
            {t('patronSearchPanel.search')}
          </button>
        </div>
      </form>

      {/* Advanced Filters Toggle */}
      <div className="mt-3 flex items-center gap-2">
        <button
          type="button"
          onClick={() => setIsAdvancedOpen(!isAdvancedOpen)}
          className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream flex items-center gap-1 transition-colors"
        >
          {isAdvancedOpen ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
          {t('patronSearchPanel.advancedFilters')}
          {activeFilterCount > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-xs font-medium bg-lsc-rose text-white rounded-full">
              {activeFilterCount}
            </span>
          )}
        </button>
        {activeFilterCount > 0 && (
          <button
            type="button"
            onClick={onClearAdvancedFilters}
            className="text-xs text-status-danger-600 dark:text-status-danger-400 hover:text-status-danger-700 dark:hover:text-status-danger-300 flex items-center gap-0.5 transition-colors"
          >
            <X className="w-3 h-3" />
            {t('patronSearchPanel.clearFilters')}
          </button>
        )}
      </div>

      {/* Advanced Filters Panel */}
      {isAdvancedOpen && (
        <div className="mt-4 pt-4 border-t border-lsc-border dark:border-earth-700 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Fines Balance Range */}
          <div>
            <label htmlFor="patron-search-fines-min" className={labelClasses}>{t('patronSearchPanel.finesMin')}</label>
            <input
              id="patron-search-fines-min"
              type="number"
              min="0"
              step="0.01"
              value={advancedFilters.finesMin ?? ""}
              onChange={(e) =>
                updateFilter("finesMin", e.target.value ? parseFloat(e.target.value) : undefined)
              }
              placeholder="0.00"
              className={inputClasses}
            />
          </div>
          <div>
            <label htmlFor="patron-search-fines-max" className={labelClasses}>{t('patronSearchPanel.finesMax')}</label>
            <input
              id="patron-search-fines-max"
              type="number"
              min="0"
              step="0.01"
              value={advancedFilters.finesMax ?? ""}
              onChange={(e) =>
                updateFilter("finesMax", e.target.value ? parseFloat(e.target.value) : undefined)
              }
              placeholder="0.00"
              className={inputClasses}
            />
          </div>

          {/* Checkout Count Min */}
          <div>
            <label htmlFor="patron-search-checkout-count-min" className={labelClasses}>{t('patronSearchPanel.checkoutCountMin')}</label>
            <input
              id="patron-search-checkout-count-min"
              type="number"
              min="0"
              step="1"
              value={advancedFilters.checkoutCountMin ?? ""}
              onChange={(e) =>
                updateFilter("checkoutCountMin", e.target.value ? parseInt(e.target.value, 10) : undefined)
              }
              placeholder="0"
              className={inputClasses}
            />
          </div>

          {/* Has Overdue */}
          <div>
            <label htmlFor="patron-search-has-overdue" className={labelClasses}>{t('patronSearchPanel.overdueItems')}</label>
            <select
              id="patron-search-has-overdue"
              value={advancedFilters.hasOverdue ?? "all"}
              onChange={(e) => {
                const val = e.target.value as OverdueFilter
                updateFilter("hasOverdue", val === "all" ? undefined : val)
              }}
              className={inputClasses}
            >
              <option value="all">{t('patronSearchPanel.overdueAll')}</option>
              <option value="has_overdue">{t('patronSearchPanel.overdueYes')}</option>
              <option value="no_overdue">{t('patronSearchPanel.overdueNo')}</option>
            </select>
          </div>

          {/* Card Status */}
          <div>
            <label className={labelClasses} htmlFor="patron-card-status-filter">
              {t('patronSearchPanel.cardStatusLabel')}
            </label>
            <select
              id="patron-card-status-filter"
              value={advancedFilters.cardStatus ?? "any"}
              onChange={(e) => {
                const val = e.target.value as CardStatusFilter
                updateFilter("cardStatus", val === "any" ? undefined : val)
              }}
              className={inputClasses}
            >
              <option value="any">{t('patronSearchPanel.cardStatusAny')}</option>
              <option value="active">{t('patronSearchPanel.cardStatusActive')}</option>
              <option value="expiring_30d">{t('patronSearchPanel.cardStatusExpiring30d')}</option>
              <option value="expiring_90d">{t('patronSearchPanel.cardStatusExpiring90d')}</option>
              <option value="expired">{t('patronSearchPanel.cardStatusExpired')}</option>
            </select>
          </div>

          {/* Member Since */}
          <div>
            <label htmlFor="patron-search-member-since" className={labelClasses}>{t('patronSearchPanel.memberSince')}</label>
            <input
              id="patron-search-member-since"
              type="date"
              value={advancedFilters.memberSinceFrom ?? ""}
              onChange={(e) =>
                updateFilter("memberSinceFrom", e.target.value || undefined)
              }
              className={inputClasses}
            />
          </div>

          {/* Member Before */}
          <div>
            <label htmlFor="patron-search-member-before" className={labelClasses}>{t('patronSearchPanel.memberBefore')}</label>
            <input
              id="patron-search-member-before"
              type="date"
              value={advancedFilters.memberSinceTo ?? ""}
              onChange={(e) =>
                updateFilter("memberSinceTo", e.target.value || undefined)
              }
              className={inputClasses}
            />
          </div>
        </div>
      )}
    </div>
  )
}
