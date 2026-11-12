/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import { X, Info, AlertTriangle } from 'lucide-react'
import { t } from '@/i18n'

const LANGUAGE_OPTIONS = [
  { code: 'eng', label: 'English' },
  { code: 'spa', label: 'Spanish' },
  { code: 'fre', label: 'French' },
  { code: 'ger', label: 'German' },
  { code: 'por', label: 'Portuguese' },
  { code: 'chi', label: 'Chinese' },
  { code: 'jpn', label: 'Japanese' },
  { code: 'ara', label: 'Arabic' },
  { code: 'rus', label: 'Russian' },
  { code: 'ita', label: 'Italian' },
]

const CURRENT_YEAR = new Date().getFullYear()

export interface FilterState {
  title: string
  author: string
  subject: string
  genre: string
  language: string
  year_min: string
  year_max: string
}

export const EMPTY_FILTERS: FilterState = {
  title: '',
  author: '',
  subject: '',
  genre: '',
  language: '',
  year_min: '',
  year_max: '',
}

export function BibframeFilterPanel({
  filters,
  onFilterChange,
  onClearFilters,
  hasFilters,
}: {
  filters: FilterState
  onFilterChange: (field: keyof FilterState, value: string) => void
  onClearFilters: () => void
  hasFilters: boolean
}): React.ReactElement {
  const inputClass = "w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose"
  const labelClass = "block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1.5"

  return (
    <div
      id="bibframe-filter-panel"
      role="region"
      aria-label={t('aria.bibframeCatalog.bibframeSearchFilters')}
      className="bg-lsc-cream/60 dark:bg-earth-800/60 rounded-xl border border-lsc-rose/20 dark:border-lsc-rose/10 p-5 space-y-4"
    >
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">
          BIBFRAME Filters
        </h2>
        {hasFilters && (
          <button
            type="button"
            onClick={onClearFilters}
            className="text-xs text-lsc-rose hover:underline flex items-center gap-1"
          >
            <X className="w-3.5 h-3.5" aria-hidden="true" />
            Clear all filters
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <label htmlFor="bf-filter-title" className={labelClass}>
            Title contains
          </label>
          <input
            id="bf-filter-title"
            type="text"
            value={filters.title}
            onChange={(e) => onFilterChange('title', e.target.value)}
            maxLength={200}
            placeholder={t('placeholder.bibframeCatalog.filterByTitle')}
            className={inputClass}
          />
        </div>

        <div>
          <label htmlFor="bf-filter-author" className={labelClass}>
            Author / Creator
          </label>
          <input
            id="bf-filter-author"
            type="text"
            value={filters.author}
            onChange={(e) => onFilterChange('author', e.target.value)}
            maxLength={200}
            placeholder={t('placeholder.bibframeCatalog.filterByAuthor')}
            className={inputClass}
          />
        </div>

        <div>
          <label htmlFor="bf-filter-subject" className={labelClass}>
            Subject
          </label>
          <input
            id="bf-filter-subject"
            type="text"
            value={filters.subject}
            onChange={(e) => onFilterChange('subject', e.target.value)}
            maxLength={200}
            placeholder={t('placeholder.bibframeCatalog.filterBySubject')}
            className={inputClass}
          />
        </div>

        <div>
          <label htmlFor="bf-filter-genre" className={labelClass}>
            Genre / Form
          </label>
          <input
            id="bf-filter-genre"
            type="text"
            value={filters.genre}
            onChange={(e) => onFilterChange('genre', e.target.value)}
            maxLength={200}
            placeholder={t('placeholder.bibframeCatalog.egFictionBiography')}
            className={inputClass}
          />
        </div>

        <div>
          <label htmlFor="bf-filter-language" className={labelClass}>
            Language
          </label>
          <select
            id="bf-filter-language"
            value={filters.language}
            onChange={(e) => onFilterChange('language', e.target.value)}
            className={inputClass}
          >
            <option value="">Any Language</option>
            {LANGUAGE_OPTIONS.map((l) => (
              <option key={l.code} value={l.code}>{l.label} ({l.code})</option>
            ))}
          </select>
        </div>

        <div>
          <label className={labelClass}>
            Publication Year Range
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={filters.year_min}
              onChange={(e) => {
                const value = e.target.value
                if (value === '' || (Number(value) >= 1000 && Number(value) <= CURRENT_YEAR + 5)) {
                  onFilterChange('year_min', value)
                }
              }}
              min={1000}
              max={CURRENT_YEAR + 5}
              placeholder={t('placeholder.bibframeCatalog.from')}
              aria-label={t('aria.bibframeCatalog.yearFrom')}
              className={inputClass}
            />
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70 text-xs flex-shrink-0">—</span>
            <input
              type="number"
              value={filters.year_max}
              onChange={(e) => {
                const value = e.target.value
                if (value === '' || (Number(value) >= 1000 && Number(value) <= CURRENT_YEAR + 5)) {
                  onFilterChange('year_max', value)
                }
              }}
              min={1000}
              max={CURRENT_YEAR + 5}
              placeholder={t('placeholder.bibframeCatalog.to')}
              aria-label={t('aria.bibframeCatalog.yearTo')}
              className={inputClass}
            />
          </div>
          {filters.year_min && filters.year_max && Number(filters.year_min) > Number(filters.year_max) && (
            <p className="mt-1 text-xs text-status-warning-600 dark:text-status-warning-400 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" aria-hidden="true" />
              "From" year is after "To" year
            </p>
          )}
        </div>
      </div>

      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1.5 pt-1">
        <Info className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
        Author and subject filters search within BIBFRAME Work metadata fields. For precise authority-controlled searches, use the Linked Data or SPARQL tools.
      </p>
    </div>
  )
}
