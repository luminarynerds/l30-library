/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Filter, X, Search, ArrowUpDown } from 'lucide-react'
import { ReadingProgramFilters } from '@/api/api'
import { PROGRAM_TYPES } from '@/config/program-types'
import { t } from '@/i18n'

export type SortOption = 'popular' | 'newest' | 'ending_soon' | 'alphabetical'

interface ProgramFiltersProps {
  filters: ReadingProgramFilters
  onChange: (filters: ReadingProgramFilters) => void
  searchQuery?: string
  onSearchChange?: (query: string) => void
  sortBy?: SortOption
  onSortChange?: (sort: SortOption) => void
}

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'popular', label: 'Most Popular' },
  { value: 'newest', label: 'Newest First' },
  { value: 'ending_soon', label: 'Ending Soon' },
  { value: 'alphabetical', label: 'A to Z' },
]

export default function ProgramFilters({
  filters,
  onChange,
  searchQuery = '',
  onSearchChange,
  sortBy = 'popular',
  onSortChange,
}: ProgramFiltersProps): React.ReactElement {
  const handleTypeChange = (type: string | null) => {
    const newFilters: ReadingProgramFilters = {
      ...filters,
    }
    if (type === null) {
      delete newFilters.program_type
    } else {
      newFilters.program_type = type as 'summer' | 'winter' | 'year_round' | 'special'
    }
    onChange(newFilters)
  }

  const handleActiveChange = (activeOnly: boolean) => {
    onChange({
      ...filters,
      active_only: activeOnly,
    })
  }

  const hasActiveFilters = filters.program_type || filters.active_only || searchQuery

  return (
    <div className="space-y-5">
      {/* Search */}
      {onSearchChange && (
        <div className="space-y-2">
          <label htmlFor="program-search" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
            Search Programs
          </label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
            <input
              id="program-search"
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={t('placeholder.programFilters.searchByName')}
              className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/70 dark:placeholder:text-lsc-cream/60 focus:outline-none focus:ring-2 focus:ring-lsc-rose text-sm"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors"
                aria-label={t('aria.advancedStaffSearchModal.clearSearch')}
              >
                <X className="w-3.5 h-3.5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Sort */}
      {onSortChange && (
        <div className="space-y-2">
          <label htmlFor="program-sort" className="flex items-center gap-1.5 text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
            <ArrowUpDown className="w-3.5 h-3.5" aria-hidden="true" />
            Sort By
          </label>
          <select
            id="program-sort"
            value={sortBy}
            onChange={(e) => onSortChange(e.target.value as SortOption)}
            className="w-full px-3 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose cursor-pointer"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      )}

      <hr className="border-lsc-border dark:border-earth-700" />

      <div className="flex items-center gap-2">
        <Filter className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        <h2 className="font-medium text-lsc-dark dark:text-lsc-cream">Filters</h2>
      </div>

      {/* Active programs toggle */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
          Program Status
        </label>
        <div className="flex gap-2">
          <button
            onClick={() => handleActiveChange(false)}
            className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              !filters.active_only
                ? 'bg-lsc-rose text-white'
                : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-border dark:hover:bg-lsc-brown/80'
            }`}
          >
            All
          </button>
          <button
            onClick={() => handleActiveChange(true)}
            className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              filters.active_only
                ? 'bg-lsc-rose text-white'
                : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-border dark:hover:bg-lsc-brown/80'
            }`}
          >
            Active
          </button>
        </div>
      </div>

      {/* Program type filter */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
          Program Type
        </label>
        <div className="space-y-1.5">
          <button
            onClick={() => handleTypeChange(null)}
            className={`w-full px-3 py-2.5 rounded-lg text-sm font-medium text-left transition-colors ${
              !filters.program_type
                ? 'bg-lsc-rose text-white'
                : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-border dark:hover:bg-lsc-brown/80'
            }`}
          >
            All Types
          </button>
          {PROGRAM_TYPES.map((type) => {
            const Icon = type.icon
            return (
              <button
                key={type.value}
                onClick={() => handleTypeChange(type.value)}
                className={`w-full px-3 py-2.5 rounded-lg text-sm font-medium text-left transition-colors flex items-center gap-2 ${
                  filters.program_type === type.value
                    ? 'bg-lsc-rose text-white'
                    : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-border dark:hover:bg-lsc-brown/80'
                }`}
              >
                <Icon className="w-4 h-4" aria-hidden="true" />
                {type.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Clear filters */}
      {hasActiveFilters && (
        <button
          onClick={() => {
            onChange({})
            onSearchChange?.('')
          }}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose/80 dark:hover:text-lsc-rose/80 transition-colors border border-lsc-rose/30 dark:border-lsc-rose-light/30 rounded-lg hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10"
        >
          <X className="w-4 h-4" aria-hidden="true" />
          Clear all filters
        </button>
      )}
    </div>
  )
}
