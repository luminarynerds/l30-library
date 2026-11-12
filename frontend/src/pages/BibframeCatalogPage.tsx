/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Search,
  BookOpen,
  Loader2,
  Filter,
  X,
  ArrowUpDown,
  AlertTriangle,
  Layers,
  Database,
  Package,
  ArrowLeft,
} from 'lucide-react'

import {
  searchBibframeCatalog,
  listBibframeWorks,
  type BibframeWork,
  type BibframeSearchParams,
} from '@/api/domains/catalog/bibframe-api'
import { useDebounce } from '@/hooks/useDebounce'
import { clsx } from '@/utils/helpers'
import { t } from '@/i18n'
import { WorkCard } from '../components/bibframe/WorkCard'
import { WorkDetailPanel } from '../components/bibframe/WorkDetailPanel'
import { BibframeFilterPanel, type FilterState, EMPTY_FILTERS } from '../components/bibframe/BibframeFilterPanel'
import PageContainer from '@/components/layout/PageContainer'

const SORT_OPTIONS: { value: string; label: string; sort_by: BibframeSearchParams['sort_by']; sort_direction: BibframeSearchParams['sort_direction'] }[] = [
  { value: 'relevance-desc', label: 'Relevance', sort_by: 'relevance', sort_direction: 'desc' },
  { value: 'title-asc', label: 'Title (A-Z)', sort_by: 'title', sort_direction: 'asc' },
  { value: 'title-desc', label: 'Title (Z-A)', sort_by: 'title', sort_direction: 'desc' },
  { value: 'year-desc', label: 'Year (Newest)', sort_by: 'year', sort_direction: 'desc' },
  { value: 'year-asc', label: 'Year (Oldest)', sort_by: 'year', sort_direction: 'asc' },
]

const FILTER_DEBOUNCE = 400

// eslint-disable-next-line complexity
export default function BibframeCatalogPage(): React.ReactElement {
  const [searchParams] = useSearchParams()

  const [query, setQuery] = useState(() => searchParams.get('q') ?? '')
  const [submittedQuery, setSubmittedQuery] = useState(() => searchParams.get('q') ?? '')
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS)
  const [showFilters, setShowFilters] = useState(false)
  const [sortValue, setSortValue] = useState('relevance-desc')
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedWorkId, setSelectedWorkId] = useState<number | null>(null)

  const debouncedFilters = {
    title: useDebounce(filters.title, FILTER_DEBOUNCE),
    author: useDebounce(filters.author, FILTER_DEBOUNCE),
    subject: useDebounce(filters.subject, FILTER_DEBOUNCE),
    genre: useDebounce(filters.genre, FILTER_DEBOUNCE),
    language: filters.language,
    year_min: useDebounce(filters.year_min, FILTER_DEBOUNCE),
    year_max: useDebounce(filters.year_max, FILTER_DEBOUNCE),
  }

  const searchInputRef = useRef<HTMLInputElement>(null)

  const currentSort = (SORT_OPTIONS.find((o) => o.value === sortValue) ?? SORT_OPTIONS[0])!

  const hasFilters = Object.values(filters).some(Boolean)
  const hasSearch = Boolean(submittedQuery)

  const apiParams: BibframeSearchParams = {
    ...(submittedQuery ? { q: submittedQuery } : {}),
    ...(debouncedFilters.title ? { title: debouncedFilters.title } : {}),
    ...(debouncedFilters.author ? { author: debouncedFilters.author } : {}),
    ...(debouncedFilters.subject ? { subject: debouncedFilters.subject } : {}),
    ...(debouncedFilters.genre ? { genre: debouncedFilters.genre } : {}),
    ...(debouncedFilters.language ? { language: debouncedFilters.language } : {}),
    ...(debouncedFilters.year_min ? { year_min: Number(debouncedFilters.year_min) } : {}),
    ...(debouncedFilters.year_max ? { year_max: Number(debouncedFilters.year_max) } : {}),
    ...(currentSort.sort_by ? { sort_by: currentSort.sort_by } : {}),
    ...(currentSort.sort_direction ? { sort_direction: currentSort.sort_direction } : {}),
    page: currentPage,
    per_page: 20,
  }

  const useSearch = hasSearch || hasFilters

  const {
    data,
    isLoading,
    error,
    isFetching,
  } = useQuery({
    queryKey: ['bibframe-catalog', apiParams],
    queryFn: () =>
      useSearch
        ? searchBibframeCatalog(apiParams)
        : listBibframeWorks(currentPage, 20),
    staleTime: 1000 * 60 * 30,
  })

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault()
        searchInputRef.current?.focus()
      }
      if (e.key === 'Escape' && selectedWorkId) {
        setSelectedWorkId(null)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [selectedWorkId])

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setSubmittedQuery(query)
    setCurrentPage(1)
  }

  function handleClearSearch() {
    setQuery('')
    setSubmittedQuery('')
    setCurrentPage(1)
    searchInputRef.current?.focus()
  }

  function handleClearFilters() {
    setFilters(EMPTY_FILTERS)
    setCurrentPage(1)
  }

  function handleFilterChange(field: keyof FilterState, value: string) {
    setFilters((prev) => ({ ...prev, [field]: value }))
    setCurrentPage(1)
  }

  function handleSortChange(value: string) {
    setSortValue(value)
    setCurrentPage(1)
  }

  const totalPages = data?.pages ?? 1
  const totalItems = data?.total ?? 0

  return (
    <PageContainer className="space-y-8 py-8">
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Link
            to="/catalog"
            className="inline-flex items-center gap-1.5 text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Standard Catalog
          </Link>
        </div>

        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
              <Layers className="w-7 h-7 text-lsc-rose flex-shrink-0" aria-hidden="true" />
              BIBFRAME Catalog
            </h1>
            <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm leading-relaxed max-w-2xl">
              Browse the catalog using the{' '}
              <a
                href="https://www.loc.gov/bibframe/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-lsc-rose hover:underline"
              >
                BIBFRAME
              </a>{' '}
              data model — a modern Library of Congress standard that organises resources into{' '}
              <strong>Works</strong> (the idea), <strong>Instances</strong> (editions / formats), and{' '}
              <strong>Items</strong> (physical copies on the shelf).
            </p>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-cream dark:bg-earth-800 rounded-lg px-3 py-2 flex-shrink-0">
            <Database className="w-3.5 h-3.5" aria-hidden="true" />
            Results cached up to 1 hr
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap pt-1">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-lsc-rose text-white text-xs font-semibold">
            <Layers className="w-3 h-3" aria-hidden="true" />
            Work — abstract content
          </span>
          <span className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm" aria-hidden="true">→</span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-lsc-rose text-white text-xs font-semibold">
            <Package className="w-3 h-3" aria-hidden="true" />
            Instance — edition / format
          </span>
          <span className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm" aria-hidden="true">→</span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-status-success-600 text-white text-xs font-semibold">
            <BookOpen className="w-3 h-3" aria-hidden="true" />
            Item — physical / digital copy
          </span>
        </div>
      </div>

      <form onSubmit={handleSearch} className="max-w-2xl">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70"
              aria-hidden="true"
            />
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              maxLength={500}
              placeholder={t('placeholder.bibframeCatalog.searchTitlesSubjectsPress')}
              aria-label={t('aria.bibframeCatalog.searchBibframeCatalog')}
              className="w-full pl-10 pr-10 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
            {query && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                aria-label={t('aria.advancedStaffSearchModal.clearSearch')}
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>
            )}
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="px-5 py-3 rounded-xl bg-lsc-rose hover:bg-lsc-rose/90 text-white font-semibold shadow-sm disabled:opacity-50 transition-colors"
          >
            {isLoading ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" aria-label={t('aria.bibframeCatalog.searching')} /> : 'Search'}
          </button>
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            aria-expanded={showFilters}
            aria-controls="bibframe-filter-panel"
            className={clsx(
              'px-4 py-3 rounded-xl border-2 font-medium flex items-center gap-2 transition-colors',
              showFilters
                ? 'bg-lsc-rose text-white border-lsc-rose'
                : 'border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-800'
            )}
          >
            <Filter className="w-4 h-4" aria-hidden="true" />
            <span className="hidden sm:inline">Filters</span>
            {hasFilters && (
              <span className="bg-lsc-white dark:bg-earth-800 text-lsc-rose text-xs px-1.5 py-0.5 rounded-full font-bold">
                {Object.values(filters).filter(Boolean).length}
              </span>
            )}
          </button>
        </div>
      </form>

      {showFilters && (
        <BibframeFilterPanel
          filters={filters}
          onFilterChange={handleFilterChange}
          onClearFilters={handleClearFilters}
          hasFilters={hasFilters}
        />
      )}

      <div className="flex items-center justify-between gap-4 flex-wrap">
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {isLoading ? (
            'Loading…'
          ) : (
            <>
              <span className="font-medium text-lsc-dark dark:text-lsc-cream">{totalItems.toLocaleString()}</span>
              {' '}Work{totalItems !== 1 ? 's' : ''} found
              {(isFetching && !isLoading) && (
                <span className="ml-2 text-lsc-rose text-xs">(refreshing…)</span>
              )}
            </>
          )}
        </p>

        <div className="flex items-center gap-2">
          <label htmlFor="bf-sort" className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
            <ArrowUpDown className="w-4 h-4" aria-hidden="true" />
            <span className="hidden sm:inline">Sort by</span>
          </label>
          <select
            id="bf-sort"
            value={sortValue}
            onChange={(e) => handleSortChange(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div aria-live="polite" aria-atomic="false">
        {isLoading && (
          <div className="space-y-4" aria-label={t('aria.bibframeCatalog.loadingBibframeWorks')}>
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="h-28 rounded-lg bg-lsc-cream dark:bg-earth-800 motion-safe:animate-pulse"
                aria-hidden="true"
              />
            ))}
          </div>
        )}

        {error && !isLoading && (
          <div className="text-center py-12 space-y-3" role="alert">
            <AlertTriangle className="w-12 h-12 mx-auto text-status-warning-500" aria-hidden="true" />
            <p className="text-lsc-dark/80 dark:text-lsc-cream/80 font-medium">
              Unable to load BIBFRAME catalog
            </p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              The catalog service may be temporarily unavailable. Please try again shortly.
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm"
            >
              Retry
            </button>
          </div>
        )}

        {!isLoading && !error && data && data.items.length === 0 && (
          <div className="text-center py-16 space-y-4">
            <BookOpen className="w-16 h-16 mx-auto text-lsc-dark/20 dark:text-lsc-cream/20" aria-hidden="true" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-lg font-medium">
              No Works found
            </p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 max-w-sm mx-auto">
              {hasSearch || hasFilters
                ? 'Try adjusting your search terms or clearing some filters.'
                : 'The BIBFRAME catalog is empty. Records can be imported from MARC or cataloged directly.'}
            </p>
            {(hasSearch || hasFilters) && (
              <div className="flex items-center justify-center gap-3">
                {hasSearch && (
                  <button
                    type="button"
                    onClick={handleClearSearch}
                    className="px-4 py-2 rounded-lg border border-lsc-rose/30 text-lsc-rose text-sm hover:bg-lsc-rose/10"
                  >
                    Clear search
                  </button>
                )}
                {hasFilters && (
                  <button
                    type="button"
                    onClick={handleClearFilters}
                    className="px-4 py-2 rounded-lg border border-lsc-rose/30 text-lsc-rose text-sm hover:bg-lsc-rose/10"
                  >
                    Clear filters
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {!isLoading && !error && data && data.items.length > 0 && (
          <div className="space-y-4">
            {data.items.map((work: BibframeWork) => (
              <WorkCard
                key={work.id}
                work={work}
                onClick={(id) => setSelectedWorkId(id)}
              />
            ))}
          </div>
        )}
      </div>

      {!isLoading && totalPages > 1 && (
        <nav aria-label={t('aria.bibframeCatalog.bibframeCatalogPagination')} className="flex items-center justify-center gap-2 pt-2">
          <button
            type="button"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream disabled:opacity-40 disabled:cursor-not-allowed hover:bg-lsc-cream dark:hover:bg-earth-800 text-sm"
          >
            Previous
          </button>
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 px-3">
            Page {currentPage} of {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream disabled:opacity-40 disabled:cursor-not-allowed hover:bg-lsc-cream dark:hover:bg-earth-800 text-sm"
          >
            Next
          </button>
        </nav>
      )}

      {selectedWorkId !== null && (
        <WorkDetailPanel
          workId={selectedWorkId}
          onClose={() => setSelectedWorkId(null)}
        />
      )}
    </PageContainer>
  )
}
