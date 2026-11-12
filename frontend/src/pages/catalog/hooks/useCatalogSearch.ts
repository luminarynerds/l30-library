/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-hooks/exhaustive-deps */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useSearchParams } from 'react-router-dom'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { type CatalogSortBy, type CatalogSortDirection } from '@/api/api'
import { unifiedSearch, fetchCatalogFacets, EMPTY_FACETS, type ContentFormat, type ContentSource } from '@/api/domains/catalog/unified-search-api'
import { type SearchSuggestion } from '@/api/pg-search-api'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import { useTranslation } from '@/i18n/I18nContext'
import { SEARCH_PREFS_KEY } from '@/pages/catalog/utils/catalogPageConstants'
import { useCatalogDebouncedFilters } from '@/pages/catalog/hooks/useCatalogDebouncedFilters'
import { FORMAT_LABELS } from '@/pages/catalog/utils/catalogHelpers'
import { useCatalogViewMode } from '@/pages/catalog/hooks/useCatalogViewMode'
import { itemMatchesAccess, READING_TIME_BRACKETS, TOPIC_FILTERS } from '@/pages/catalog/utils/catalogFilterData'
import { clean } from '@/lib/utils'
import { CATALOG_SORT_VALUES, FACET_GROUP_LABELS, QUIET_BANNER_KEY, SORT_OPTIONS } from '@/pages/catalog/utils/catalogSearchConstants'
import { getGentleResultsMessage } from '@/pages/catalog/utils/catalogSearchCopy'
import { toDisplayItem, type CatalogDisplayItem } from '@/pages/catalog/utils/catalogDisplayItem'
import { speakText, stopSpeaking } from '@/pages/catalog/utils/catalogTextToSpeech'
import { buildActiveFilterChips, EMPTY_FILTERS, type CatalogFilters } from '@/pages/catalog/utils/catalogFilters'
import {
  hasAnyFilterUrlParam,
  parseFiltersFromUrl,
  parseSiblingBoolsFromUrl,
  serializeFiltersToUrl,
  serializeSiblingBoolsToUrl,
} from '@/pages/catalog/filters/url'
import {
  readFiltersFromStorage,
  readSiblingBoolsFromStorage,
  writeFiltersToStorage,
  writeSiblingBoolsToStorage,
} from '@/pages/catalog/filters/storage'
import { useCatalogKeyboardShortcuts } from '@/pages/catalog/hooks/useCatalogKeyboardShortcuts'
import { useCatalogSuggestions } from '@/pages/catalog/hooks/useCatalogSuggestions'
import { useCatalogLandingData } from '@/pages/catalog/hooks/useCatalogLandingData'
import { fetchSavedSearch, type SavedSearch } from '@/pages/catalog/hooks/useSavedSearches'

// Re-export the public API consumed by other modules.
export { QUIET_BANNER_KEY, SORT_OPTIONS } from '@/pages/catalog/utils/catalogSearchConstants'
export { formatResultsCount, toTitleCaseLabel } from '@/pages/catalog/utils/catalogSearchCopy'
export type { CatalogDisplayItem } from '@/pages/catalog/utils/catalogDisplayItem'
export type { CatalogFilters } from '@/pages/catalog/utils/catalogFilters'

const ITEM_HEIGHT = 160
const NON_BOOK_FORMATS: ContentFormat[] = ['ebook', 'audiobook', 'dvd', 'bluray', 'cd', 'vinyl', 'magazine', 'game', 'equipment', 'kit', 'tool', 'video_streaming', 'music']

export function getInitialLargePrintOnly(params: URLSearchParams): boolean {
  return parseSiblingBoolsFromUrl(params).showLargePrintOnly ?? false
}

export function getSelectedFacetInput(filters: CatalogFilters) {
  return {
    subject_facets: filters.subject_facets.length ? filters.subject_facets : undefined,
    author_facets: filters.author_facets.length ? filters.author_facets : undefined,
    series_facets: filters.series_facets.length ? filters.series_facets : undefined,
  }
}

export function hasClientPostFilters(filters: CatalogFilters): boolean {
  return filters.access === 'has_audio'
}

export function getSemanticFilterInput(filters: CatalogFilters) {
  const reading = READING_TIME_BRACKETS.find((item) => item.value === filters.reading_time)
  const topic = TOPIC_FILTERS.find((item) => item.value === filters.topic)
  const shortGentle = filters.access === 'short_gentle'
  const visualGraphic = filters.access === 'visual_graphic'
  return {
    min_pages: reading && 'minPages' in reading ? reading.minPages : undefined,
    max_pages: shortGentle ? 200 : reading && 'maxPages' in reading ? reading.maxPages - 1 : undefined,
    subject_facets: topic?.match ?? (visualGraphic ? ['Graphic Novels'] : undefined),
  }
}

export function getCatalogResultWindow(
  clientPostFiltersActive: boolean,
  preferPagination: boolean,
  currentPage: number,
) {
  if (clientPostFiltersActive) return { limit: 100, offset: 0 }
  return {
    limit: preferPagination ? 20 : 100,
    offset: preferPagination ? (currentPage - 1) * 20 : 0,
  }
}

export function useCatalogSearch() {
  const {
    quietMode,
    focusMode,
    simplifiedView: accessibilitySimplifiedView,
    reduceMotion,
    showImages: accessibilityShowImages,
    preferPagination,
    noFOMO,
    keyboardShortcutsEnabled,
    announceToScreenReader,
    updateSetting: updateA11ySetting,
  } = useUnifiedAccessibility()
  const { t } = useTranslation()

  const [searchParams, setSearchParams] = useSearchParams()
  // Read URL params directly from window.location to avoid stale searchParams
  // when React Router's v7_startTransition wraps navigation in a transition
  const initialParams = useRef(new URLSearchParams(window.location.search))
  const isInitialMount = useRef(true)

  const initialSubject = initialParams.current.get('subject') || ''
  const [searchQuery, setSearchQuery] = useState(() => initialSubject || initialParams.current.get('q') || '')
  const [submittedQuery, setSubmittedQuery] = useState(() => initialSubject || initialParams.current.get('q') || '')
  const [subjectFilter, _setSubjectFilter] = useState(initialSubject)
  const [showNewArrivals, setShowNewArrivals] = useState(
    () => parseSiblingBoolsFromUrl(initialParams.current).showNewArrivals ?? false,
  )
  const [showLargePrintOnly, setShowLargePrintOnly] = useState(
    () => getInitialLargePrintOnly(initialParams.current),
  )
  const [simplifiedView, setSimplifiedView] = useState(accessibilitySimplifiedView)
  const [speakingItemId, setSpeakingItemId] = useState<number | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [sortBy, setSortBy] = useState<CatalogSortBy>(() => {
    const urlSort = initialParams.current.get('sort')
    // Default browse sort is popularity (circulation count) so the first
    // tiles of a fresh /catalog are titles patrons actually borrow, not the
    // lowest-id legacy records. A search query overrides to relevance below
    // (handleSearch keeps the selected sort; the search path scores by rank).
    return urlSort && CATALOG_SORT_VALUES.includes(urlSort)
      ? urlSort as CatalogSortBy
      : 'popularity'
  })
  const [sortDirection, setSortDirection] = useState<CatalogSortDirection>(() => {
    const urlDir = initialParams.current.get('sort_dir')
    return urlDir === 'asc' || urlDir === 'desc' ? urlDir : 'desc'
  })
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [showQuietBanner, setShowQuietBanner] = useState(() => {
    try { return !localStorage.getItem(QUIET_BANNER_KEY) } catch { return true }
  })

  const searchInputRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)
  const virtualScrollRef = useRef<HTMLElement>(null)

  // Filter states — initialized from window.location to avoid stale searchParams race
  const [filters, setFilters] = useState<CatalogFilters>(() => ({
    ...EMPTY_FILTERS,
    ...parseFiltersFromUrl(initialParams.current),
  }))

  // Determine effective settings
  const effectiveQuietMode = quietMode || noFOMO
  const effectiveSimplifiedView = simplifiedView || accessibilitySimplifiedView
  const effectiveShowImages = accessibilityShowImages !== false

  // View mode (list / grid) -- forced to list when quiet mode is on
  const { viewMode, setViewMode, isGridDisabled } = useCatalogViewMode(effectiveQuietMode)

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { activeQuery, debouncedFilters, debouncedSearchQuery } = useCatalogDebouncedFilters(searchQuery, submittedQuery, filters as any)

  // -----------------------------------------------------------------------
  // URL <-> state sync
  // -----------------------------------------------------------------------

  // Sync type filter from URL when searchParams change (back/forward navigation)
  useEffect(() => {
    if (isInitialMount.current) return
    const urlType = parseFiltersFromUrl(searchParams).item_type
    if (urlType && urlType !== filters.item_type) {
      setFilters(prev => ({ ...prev, item_type: urlType }))
    }
  }, [searchParams])

  // Load saved search preferences (skip if URL has explicit filters)
  useEffect(() => {
    if (hasAnyFilterUrlParam(initialParams.current)) return

    try {
      const saved = localStorage.getItem(SEARCH_PREFS_KEY)
      if (!saved) return
      const prefs = JSON.parse(saved)

      if (typeof prefs !== 'object' || prefs === null) {
        localStorage.removeItem(SEARCH_PREFS_KEY)
        return
      }

      if (prefs.filters && typeof prefs.filters === 'object') {
        setFilters(readFiltersFromStorage(prefs.filters))
      }

      const siblingBools = readSiblingBoolsFromStorage(prefs)
      setShowNewArrivals(siblingBools.showNewArrivals)
      setShowLargePrintOnly(siblingBools.showLargePrintOnly)
      if (typeof prefs.simplifiedView === 'boolean') setSimplifiedView(prefs.simplifiedView)
      if (typeof prefs.sortBy === 'string' && CATALOG_SORT_VALUES.includes(prefs.sortBy)) {
        setSortBy(prefs.sortBy as CatalogSortBy)
      }
      if (typeof prefs.sortDirection === 'string' && ['asc', 'desc'].includes(prefs.sortDirection)) {
        setSortDirection(prefs.sortDirection as CatalogSortDirection)
      }
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
      localStorage.removeItem(SEARCH_PREFS_KEY)
    }
  }, [])

  // Save search preferences when they change
  useEffect(() => {
    try {
      localStorage.setItem(SEARCH_PREFS_KEY, JSON.stringify({
        filters: writeFiltersToStorage(filters),
        simplifiedView,
        ...writeSiblingBoolsToStorage({ showNewArrivals, showLargePrintOnly }),
        sortBy,
        sortDirection,
      }))
    } catch {
      // Ignore errors saving preferences
    }
  }, [filters, simplifiedView, showNewArrivals, showLargePrintOnly, sortBy, sortDirection])

  // Sync filters to URL so filtered searches are bookmarkable/shareable
  useEffect(() => {
    // Skip the first render to avoid overwriting URL params before they are read
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }

    const params = new URLSearchParams()
    if (subjectFilter) params.set('subject', subjectFilter)
    else if (searchQuery) params.set('q', searchQuery)
    // ``serializeFiltersToUrl`` now writes the multi-select facet arrays
    // (``subject_facets``, ``author_facets``, ``series_facets``) via the
    // schema-driven ``string-array`` codec, so the hand-rolled
    // ``params.append`` loops that used to live here are gone. The codec
    // also parses them back on mount, closing the silent ghost-toggle that
    // cleared the chip set on every reload or shared deep link.
    serializeFiltersToUrl(debouncedFilters, params)
    serializeSiblingBoolsToUrl({ showNewArrivals, showLargePrintOnly }, params)
    if (sortBy !== 'relevance') params.set('sort', sortBy)
    if (sortDirection !== 'desc') params.set('sort_dir', sortDirection)

    setSearchParams(params, { replace: true })
  }, [searchQuery, subjectFilter, debouncedFilters, showNewArrivals, sortBy, sortDirection])

  // -----------------------------------------------------------------------
  // Saved-search hydration
  // -----------------------------------------------------------------------

  /**
   * Populate state from a fetched SavedSearch row.
   *
   * Exposed so the SavedSearchesPanel "Run" button can replay state without a
   * page navigation; also used by the `?saved=<id>` mount-time hydrate below.
   * Single-select filter shape is preserved (see
   * [[feedback_l30_sidebar_filters_single_select]]) — extra array values get
   * dropped on the floor rather than crashing the sidebar.
   */
  const applySavedSearch = useCallback((saved: SavedSearch) => {
    const f = (saved.filters_json || {}) as Record<string, unknown>
    const pickStr = (v: unknown): string => (typeof v === 'string' ? v : '')
    setFilters(readFiltersFromStorage(f))

    const q = saved.query ?? ''
    setSearchQuery(q)
    setSubmittedQuery(q)

    if (typeof f.show_new_arrivals === 'boolean') {
      setShowNewArrivals(f.show_new_arrivals)
    } else {
      setShowNewArrivals(false)
    }
    if (typeof f.show_large_print_only === 'boolean') {
      setShowLargePrintOnly(f.show_large_print_only)
    } else {
      setShowLargePrintOnly(false)
    }

    if (saved.sort_by && CATALOG_SORT_VALUES.includes(saved.sort_by)) {
      setSortBy(saved.sort_by as CatalogSortBy)
    }
    const sortDir = pickStr(f.sort_direction)
    if (sortDir === 'asc' || sortDir === 'desc') setSortDirection(sortDir)

    setCurrentPage(1)
  }, [])

  // Mount-only: if URL contains `?saved=<id>`, fetch the saved search,
  // populate state, and strip the `saved` param so the URL becomes a clean
  // bookmarkable filter URL. Failures are silent — a bad/expired id should
  // not break the catalog page; we just fall through to the normal URL state.
  useEffect(() => {
    const savedId = initialParams.current.get('saved')
    if (!savedId) return

    let cancelled = false
    fetchSavedSearch(savedId)
      .then((saved) => {
        if (cancelled) return
        applySavedSearch(saved)
        // Strip `?saved=<id>` via history.replaceState so the back button
        // works naturally and the URL becomes shareable as a regular filter
        // URL. We can't use setSearchParams here because the filter-sync
        // effect will rewrite the URL on next tick with the right shape.
        const url = new URL(window.location.href)
        url.searchParams.delete('saved')
        window.history.replaceState(window.history.state, '', url.toString())
      })
      .catch((err: unknown) => {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      })

    return () => {
      cancelled = true
    }
  }, [applySavedSearch])

  // -----------------------------------------------------------------------
  // Keyboard shortcuts
  // -----------------------------------------------------------------------

  useCatalogKeyboardShortcuts({
    searchInputRef,
    isDrawerOpen,
    setIsDrawerOpen,
    simplifiedView,
    setSimplifiedView,
    setSpeakingItemId,
    quietMode,
    updateA11ySetting,
    announceToScreenReader,
    reduceMotion,
    shortcutsEnabled: keyboardShortcutsEnabled,
  })

  // -----------------------------------------------------------------------
  // Query
  // -----------------------------------------------------------------------

  // Single source of truth for "are any filters active": derive from the
  // same per-field chip builder the sidebar renders, rather than re-deriving
  // truthiness ad hoc. `Object.values(filters).some(v => v)` used to live
  // here, but CatalogFilters always carries subject_facets/author_facets/
  // series_facets as `[]` (see EMPTY_FILTERS) — an empty array is truthy in
  // JS, so that check was permanently `true` and the browse-by-format
  // landing panel never rendered.
  const activeFilterChips = buildActiveFilterChips(filters, showNewArrivals, showLargePrintOnly)
  const hasActiveFilters = activeFilterChips.length > 0
  const clientPostFiltersActive = hasClientPostFilters(debouncedFilters)

  const { data: rawData, isLoading, error, refetch } = useQuery({
    queryKey: ['catalog-unified', activeQuery, debouncedFilters, showNewArrivals, showLargePrintOnly, currentPage, preferPagination, sortBy, sortDirection, [...(debouncedFilters.subject_facets ?? [])].sort(), [...(debouncedFilters.author_facets ?? [])].sort(), [...(debouncedFilters.series_facets ?? [])].sort()],
    queryFn: async () => {
      const isIndieFilter = debouncedFilters.item_type === 'indie_ebook'
      const isNonBookFilter = debouncedFilters.item_type === 'non-book'
      const formats = isIndieFilter
        ? ['ebook' as ContentFormat]
        : isNonBookFilter
          ? NON_BOOK_FORMATS
          : debouncedFilters.item_type
            ? [debouncedFilters.item_type as ContentFormat]
            : undefined
      const sources = isIndieFilter ? ['indie' as ContentSource] : undefined
      const availableOnly = debouncedFilters.available_only ? true : undefined
      const { limit, offset } = getCatalogResultWindow(
        clientPostFiltersActive,
        preferPagination,
        currentPage,
      )
      const semanticFilters = getSemanticFilterInput(debouncedFilters)
      const selectedFacets = getSelectedFacetInput(debouncedFilters)
      const subjectFacets = [
        ...(selectedFacets.subject_facets ?? []),
        ...(semanticFilters.subject_facets ?? []),
      ]

      const yearMin = debouncedFilters.year_min ? parseInt(debouncedFilters.year_min) : undefined
      const yearMax = debouncedFilters.year_max ? parseInt(debouncedFilters.year_max) : undefined

      const searchInput = clean({
        query: subjectFilter || activeQuery || '*',
        formats,
        sources,
        available_only: availableOnly,
        // #889: forward holdability toggle to unified-search. The backend
        // exposes it as a Query param on /catalog/search (browse.py:441).
        available_for_hold: debouncedFilters.available_for_hold ? true : undefined,
        year_min: yearMin && !isNaN(yearMin) ? yearMin : undefined,
        year_max: yearMax && !isNaN(yearMax) ? yearMax : undefined,
        limit,
        offset,
        sort_by: sortBy,
        sort_direction: sortDirection,
        min_lexile: debouncedFilters.min_lexile ?? undefined,
        max_lexile: debouncedFilters.max_lexile ?? undefined,
        language: debouncedFilters.language ? [debouncedFilters.language] : undefined,
        is_large_print: showLargePrintOnly ? true : undefined,
        publisher: debouncedFilters.publisher || undefined,
        location: debouncedFilters.location || undefined,
        min_pages: semanticFilters.min_pages,
        max_pages: semanticFilters.max_pages,
        ...selectedFacets,
        subject_facets: subjectFacets.length > 0 ? subjectFacets : undefined,
      })

      // Run the main results query and the facets query in parallel so the
      // sidebar's subject/author/series multi-select groups receive data
      // without an extra round-trip. Facets fail-soft to EMPTY_FACETS so a
      // 500 on the facets endpoint never blanks the result grid.
      const [response, facets] = await Promise.all([
        unifiedSearch(searchInput),
        fetchCatalogFacets(searchInput).catch(() => EMPTY_FACETS),
      ])

      const items: CatalogDisplayItem[] = response.results.map(toDisplayItem)

      // Defensive check: ensure all items have valid IDs
      if (process.env.NODE_ENV !== 'production') {
        items.forEach((item, index) => {
          if (!item.id || item.id <= 0) {
            console.warn(
              `[Catalog Data Guard] Invalid item ID at index ${index}: ${item.id}. Item: ${item.title}`
            )
          }
        })
      }

      return {
        items,
        total: response.total_results,
        page: preferPagination ? currentPage : 1,
        per_page: limit,
        pages: Math.ceil(response.total_results / limit),
        facets,
        source_counts: response.source_counts,
        query_was_all_stopwords: response.query_was_all_stopwords ?? false,
      }
    },
    enabled: true,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    // Keep the previous result visible while a new query is in flight so
    // filter/keystroke changes don't blank the grid into skeletons. The
    // existing `isLoading` gate in CatalogResultsList still triggers the
    // skeleton on the very first fetch (when no prior data exists).
    placeholderData: keepPreviousData,
  })

  const { readingLists } = useCatalogLandingData()

  // -----------------------------------------------------------------------
  // Suggestions / Did-you-mean
  // -----------------------------------------------------------------------

  const {
    suggestions,
    showSuggestions,
    setShowSuggestions,
    selectedSuggestionIndex,
    setSelectedSuggestionIndex,
    didYouMean,
    setDidYouMean,
    suggestionsRef,
    resetSuggestions,
  } = useCatalogSuggestions({
    searchQuery,
    activeQuery,
    totalResults: rawData?.total,
  })

  // -----------------------------------------------------------------------
  // Virtualizer & post-filter
  // -----------------------------------------------------------------------

  const items: CatalogDisplayItem[] = rawData?.items ?? []

  // Post-filter items using client-side filter logic (memoized to avoid recomputing on every render)
  const filteredItems = useMemo(() => {
    if (!items.length) return []
    return items.filter(item => {
      if (filters.access === 'has_audio' && !itemMatchesAccess(
        { title: item.title, item_type: item.item_type, subjects: item.subjects, page_count: item.page_count },
        filters.access,
        items.map(i => ({ title: i.title, item_type: i.item_type }))
      )) return false
      return true
    })
  }, [items, filters.access])

  // reading_time/topic/access are evaluated client-side. When any is active,
  // describe only the bounded result set we actually evaluated instead of
  // claiming the backend's unfiltered total or offering misleading pages.
  const data = useMemo(() => {
    if (!rawData || !clientPostFiltersActive) return rawData
    return {
      ...rawData,
      total: filteredItems.length,
      page: 1,
      per_page: 100,
      pages: filteredItems.length > 0 ? 1 : 0,
    }
  }, [rawData, clientPostFiltersActive, filteredItems.length])

  const shouldVirtualize = !preferPagination && filteredItems.length > 20 && viewMode === 'list'

  const virtualizer = useVirtualizer({
    count: filteredItems.length,
    getScrollElement: () => virtualScrollRef.current,
    estimateSize: useCallback(() => ITEM_HEIGHT, []),
    overscan: 5,
  })

  // Announce results to screen reader
  useEffect(() => {
    if (data && (activeQuery || hasActiveFilters)) {
      const message = getGentleResultsMessage(data.total, hasActiveFilters)
      announceToScreenReader(message)
    }
  }, [data, activeQuery, hasActiveFilters, announceToScreenReader])

  // -----------------------------------------------------------------------
  // Handlers
  // -----------------------------------------------------------------------

  const handleSelectSuggestion = (suggestion: SearchSuggestion) => {
    const term = suggestion.title || ''
    setSearchQuery(term)
    setSubmittedQuery(term)
    resetSuggestions()
    setCurrentPage(1)
  }

  const handleSearch = (e: React.FormEvent): void => {
    e.preventDefault()
    setSubmittedQuery(searchQuery)
    // Submitting a real query should rank by relevance, but only when the user
    // is still on the untouched browse default (popularity). If they picked an
    // explicit sort (title, year, ...) we respect it. This keeps the
    // popularity-first browse landing while restoring relevance ranking for
    // actual searches.
    if (searchQuery.trim() && sortBy === 'popularity') {
      setSortBy('relevance')
      setSortDirection('desc')
    }
    resetSuggestions()
    setCurrentPage(1)
    setTimeout(() => {
      resultsRef.current?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth' })
    }, 100)
  }

  const handleClearFilters = () => {
    setFilters({ ...EMPTY_FILTERS })
    setShowNewArrivals(false)
    setShowLargePrintOnly(false)
    setCurrentPage(1)
    announceToScreenReader(t('catalog.filterAnnouncements.allCleared'))
  }

  const handleClearSearch = () => {
    setSearchQuery('')
    setSubmittedQuery('')
    setCurrentPage(1)
    searchInputRef.current?.focus()
    announceToScreenReader(t('catalog.filterAnnouncements.searchCleared'))
  }

  useEffect(() => {
    setSubmittedQuery(debouncedSearchQuery)
  }, [debouncedSearchQuery])

  const handleBrowseFormat = (formatType: string) => {
    setSearchQuery('')
    setSubmittedQuery('')
    setFilters({
      ...EMPTY_FILTERS,
      item_type: formatType,
    })
    setShowNewArrivals(false)
    setCurrentPage(1)
    announceToScreenReader(t('catalog.filterAnnouncements.browsing', { format: FORMAT_LABELS[formatType] || formatType }))
  }

  const handleSpeak = (text: string, itemId: number) => {
    setSpeakingItemId(itemId)
    speakText(text, () => setSpeakingItemId(null))
  }

  const handleStopSpeak = () => {
    stopSpeaking()
    setSpeakingItemId(null)
  }

  const handleSortChange = (value: string) => {
    const option = SORT_OPTIONS.find(opt => opt.value === value)
    if (option) {
      setSortBy(option.sortBy)
      setSortDirection(option.sortDirection)
      setCurrentPage(1)
    }
  }

  const handleFacetSelect = useCallback((group: string, value: string) => {
    if (group === 'item_type') {
      setFilters(prev => ({ ...prev, item_type: value || null }))
      // Browsing a format with no search query keeps the popularity default
      // (the format facet narrows; the sort stays "most borrowed first").
      // Previously this forced Title A-Z, which is exactly the dull-first-
      // impression the popularity default exists to fix.
      // Reset to relevance when clearing a format filter while a search is
      // active and the user had not picked an explicit sort.
      if (!value && submittedQuery && sortBy === 'title') {
        setSortBy('relevance')
        setSortDirection('desc')
      }
    } else if (group === 'available_only') {
      // #887: the legacy faux-enum status was collapsed to a boolean. Truthy
      // `value` (any non-empty string) enables; empty `value` clears.
      setFilters(prev => ({ ...prev, available_only: Boolean(value) }))
    } else if (group === 'available_for_hold') {
      // #889: holdability toggle. Same convention as `available_only`.
      setFilters(prev => ({ ...prev, available_for_hold: Boolean(value) }))
    } else if (group === 'location' || group === 'publisher'
      || group === 'reading_time' || group === 'access' || group === 'topic'
      || group === 'language') {
      setFilters(prev => ({ ...prev, [group]: value }))
    }
    setCurrentPage(1)
    announceToScreenReader(
      value
        ? t('catalog.filterAnnouncements.filtered', { group: FACET_GROUP_LABELS[group] || group, value })
        : t('catalog.filterAnnouncements.facetRemoved', { group: FACET_GROUP_LABELS[group] || group }),
    )
  }, [announceToScreenReader, submittedQuery, sortBy, t])

  const handleRemoveChip = (key: string, label: string) => {
    if (key.startsWith('subject_facets:')) {
      const target = key.slice('subject_facets:'.length)
      setFilters(prev => ({
        ...prev,
        subject_facets: (prev.subject_facets ?? []).filter(v => v !== target),
      }))
      setCurrentPage(1)
      announceToScreenReader(t('catalog.filterAnnouncements.removed', { label }))
      return
    }
    if (key.startsWith('author_facets:')) {
      const target = key.slice('author_facets:'.length)
      setFilters(prev => ({
        ...prev,
        author_facets: (prev.author_facets ?? []).filter(v => v !== target),
      }))
      setCurrentPage(1)
      announceToScreenReader(t('catalog.filterAnnouncements.removed', { label }))
      return
    }
    if (key.startsWith('series_facets:')) {
      const target = key.slice('series_facets:'.length)
      setFilters(prev => ({
        ...prev,
        series_facets: (prev.series_facets ?? []).filter(v => v !== target),
      }))
      setCurrentPage(1)
      announceToScreenReader(t('catalog.filterAnnouncements.removed', { label }))
      return
    }
    if (key === 'new') {
      setShowNewArrivals(false)
    } else if (key === 'large_print') {
      setShowLargePrintOnly(false)
    } else if (key === 'min_lexile' || key === 'max_lexile') {
      setFilters(prev => ({ ...prev, [key]: null }))
    } else if (key === 'available_only' || key === 'available_for_hold') {
      // #887 / #889: boolean toggles can't take '' as the cleared value.
      setFilters(prev => ({ ...prev, [key]: false }))
    } else {
      setFilters(prev => ({ ...prev, [key]: '' }))
    }
    setCurrentPage(1)
    announceToScreenReader(t('catalog.filterAnnouncements.removed', { label }))
  }

  const handleLexileChange = ({ min, max }: { min: number | null; max: number | null }) => {
    setFilters(prev => ({ ...prev, min_lexile: min, max_lexile: max }))
    setCurrentPage(1)
  }

  const onSubjectFacetsChange = useCallback(
    (next: string[]) =>
      setFilters(prev => ({ ...prev, subject_facets: next.slice(0, 20) })),
    [],
  )

  const onAuthorFacetsChange = useCallback(
    (next: string[]) =>
      setFilters(prev => ({ ...prev, author_facets: next.slice(0, 20) })),
    [],
  )

  const onSeriesFacetsChange = useCallback(
    (next: string[]) =>
      setFilters(prev => ({ ...prev, series_facets: next.slice(0, 20) })),
    [],
  )

  const handleEnableQuietFromBanner = () => {
    updateA11ySetting('quietMode', true)
    setShowQuietBanner(false)
    localStorage.setItem(QUIET_BANNER_KEY, 'true')
    announceToScreenReader(t('catalog.filterAnnouncements.quietModeEnabled'))
  }

  const handleDismissQuietBanner = () => {
    setShowQuietBanner(false)
    localStorage.setItem(QUIET_BANNER_KEY, 'true')
  }

  const handleDidYouMeanClick = (term: string) => {
    setSearchQuery(term)
    setSubmittedQuery(term)
    setDidYouMean(null)
    setCurrentPage(1)
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  // -----------------------------------------------------------------------
  // Derived
  // -----------------------------------------------------------------------

  const currentSortValue = SORT_OPTIONS.find(
    opt => opt.sortBy === sortBy && opt.sortDirection === sortDirection,
  )?.value || 'relevance'

  return {
    // Accessibility settings
    focusMode,
    effectiveQuietMode,
    effectiveSimplifiedView,
    effectiveShowImages,
    reduceMotion,
    preferPagination,

    // Search state
    searchQuery,
    setSearchQuery,
    activeQuery,
    suggestions,
    showSuggestions,
    setShowSuggestions,
    selectedSuggestionIndex,
    setSelectedSuggestionIndex,
    didYouMean,

    // Refs
    searchInputRef,
    resultsRef,
    virtualScrollRef,
    suggestionsRef,

    // Filter state
    filters,
    showNewArrivals,
    setShowNewArrivals,
    showLargePrintOnly,
    setShowLargePrintOnly,
    hasActiveFilters,
    activeFilterChips,
    isDrawerOpen,
    setIsDrawerOpen,

    // Sort state
    currentSortValue,
    sortBy,
    sortDirection,

    // View mode
    viewMode,
    setViewMode,
    isGridDisabled,

    // Query results
    data,
    isLoading,
    error: error as Error | null,
    refetch,
    filteredItems,
    readingLists,

    // Virtualizer
    shouldVirtualize,
    virtualizer,

    // Speaking state
    speakingItemId,

    // Banner
    showQuietBanner,

    // Pagination
    currentPage,

    // Handlers
    handleSearch,
    handleClearSearch,
    handleSelectSuggestion,
    handleClearFilters,
    handleBrowseFormat,
    handleSpeak,
    handleStopSpeak,
    handleSortChange,
    handleFacetSelect,
    handleRemoveChip,
    handleLexileChange,
    onSubjectFacetsChange,
    onAuthorFacetsChange,
    onSeriesFacetsChange,
    handleEnableQuietFromBanner,
    handleDismissQuietBanner,
    handleDidYouMeanClick,
    handlePageChange,
    applySavedSearch,
  }
}
