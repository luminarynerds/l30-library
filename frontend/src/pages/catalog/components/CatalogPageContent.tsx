/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n/I18nContext'
import { clsx } from '@/utils/helpers'
import { useCatalogSearch, SORT_OPTIONS, formatResultsCount } from '@/pages/catalog/hooks/useCatalogSearch'
import CatalogFilterSidebar, { MobileFilterButton } from '@/pages/catalog/components/CatalogFilterSidebar'
import { SEARCH_PREFS_KEY } from '@/pages/catalog/utils/catalogPageConstants'
import CatalogViewToggle from '@/pages/catalog/components/CatalogViewToggle'
import CatalogSearchBar from '@/pages/catalog/components/CatalogSearchBar'
import CatalogDisplayMenu from '@/pages/catalog/components/CatalogDisplayMenu'
import CatalogResultsList from '@/pages/catalog/components/CatalogResultsList'
import CatalogLandingPanel from '@/pages/catalog/components/CatalogLandingPanel'
import FilterChip from '@/pages/catalog/components/FilterChip'
import MoodLegend from '@/pages/catalog/components/MoodLegend'
import { useShelfStatusMap } from '@/hooks/useShelfStatusMap'
import { useAvailabilityMap } from '@/hooks/useAvailabilityMap'
import { useJourneyTracker } from '@/hooks/useJourneyTracker'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { useChallengedItemIds } from '@/pages/catalog/hooks/useChallengedItemIds'
import SaveThisSearchButton from '@/pages/catalog/components/SaveThisSearchButton'
import SavedSearchesPanel from '@/pages/catalog/components/SavedSearchesPanel'
import { useAuth } from '@/contexts/AuthContext'
import { fetchSavedSearch } from '@/pages/catalog/hooks/useSavedSearches'
import { getInitialHideCovers } from '@/pages/catalog/utils/networkAwareDefaults'
import { useCatalogPageStateRestore } from '@/pages/catalog/hooks/useCatalogPageStateRestore'
import { X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import ShelfBanner from '@/components/discover/ShelfBanner'

// Re-export for backward compatibility
export type { CatalogDisplayItem } from '@/pages/catalog/hooks/useCatalogSearch'

// ---------------------------------------------------------------------------
// Copy (kept for screen reader live region)
// ---------------------------------------------------------------------------

function getGentleResultsMessage(total: number, hasFilters: boolean, t: (key: string, params?: Record<string, unknown>) => string): string {
  if (total === 0) {
    return hasFilters ? t('catalog.noFilterMatches') : t('catalog.noSearchMatches')
  }
  if (total === 1) {
    return t('catalog.singleResult')
  }
  return `${formatResultsCount(total)}. ${t('catalog.multiResultNextStep')}`
}

// ---------------------------------------------------------------------------
// CatalogPage (thin orchestrator)
// ---------------------------------------------------------------------------

export default function CatalogPage(): React.ReactElement {
  const { t } = useTranslation()
  const {
    // Accessibility
    focusMode,
    effectiveQuietMode,
    effectiveSimplifiedView,
    effectiveShowImages,
    reduceMotion,
    preferPagination,

    // Search
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

    // Filters
    filters,
    showNewArrivals,
    setShowNewArrivals,
    showLargePrintOnly,
    setShowLargePrintOnly,
    hasActiveFilters,
    activeFilterChips,
    isDrawerOpen,
    setIsDrawerOpen,

    // Sort
    currentSortValue,

    // View mode
    viewMode,
    setViewMode,
    isGridDisabled,

    // Query results
    data,
    isLoading,
    error,
    refetch,
    filteredItems,
    readingLists,

    // Virtualizer
    shouldVirtualize,
    virtualizer,

    // Speaking
    speakingItemId,

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
    handleDidYouMeanClick,
    handlePageChange,
    applySavedSearch,
    sortBy,
    sortDirection,
  } = useCatalogSearch()

  const { trackStage } = useJourneyTracker({ journeyType: "search_to_hold" })
  const searchTrackedRef = useRef(false)

  // Track search_initiated when user submits a search
  useEffect(() => {
    if (activeQuery && !searchTrackedRef.current) {
      trackStage("search_initiated")
      searchTrackedRef.current = true
    }
    if (!activeQuery) searchTrackedRef.current = false
  }, [activeQuery]) // eslint-disable-line react-hooks/exhaustive-deps

  // Track results_displayed when data arrives
  useEffect(() => {
    if (data && activeQuery) {
      trackStage("results_displayed", { results_count: filteredItems.length })
    }
  }, [data]) // eslint-disable-line react-hooks/exhaustive-deps

  // Restore scroll/drawer/viewMode on back-navigation (sessionStorage, per-route).
  // Scroll restore waits until results are in the DOM so the page is tall enough.
  useCatalogPageStateRestore({
    resultsReady: !isLoading && data !== undefined,
    isDrawerOpen,
    setIsDrawerOpen,
    viewMode,
    setViewMode,
  })

  const shelfStatusMap = useShelfStatusMap()
  // Copy-level availability for local items on the current results page.
  // One batched POST per page (mirrors useShelfStatusMap's per-page pattern).
  const availabilityMap = useAvailabilityMap(
    filteredItems.filter((i) => !i.source || i.source === 'local').map((i) => i.id),
  )

  const { isFeatureEnabled } = useOrganizationFeatures()
  const challengedItemIds = useChallengedItemIds(isFeatureEnabled('banned_books_tracking_enabled'))
  const { isAuthenticated, user } = useAuth()
  const savedSearchesEnabled = isFeatureEnabled('saved_searches_enabled')
  const showSavedSearchesUi = savedSearchesEnabled && isAuthenticated

  // "Run" handler for the panel — push ?saved=<id> so the URL is shareable,
  // fetch the row, and replay state via applySavedSearch. The hook strips
  // `?saved=` from the URL once hydrate is complete.
  const handleRunSavedSearch = async (id: string): Promise<void> => {
    try {
      const url = new URL(window.location.href)
      url.searchParams.set('saved', id)
      window.history.replaceState(window.history.state, '', url.toString())
      const saved = await fetchSavedSearch(id)
      applySavedSearch(saved)
      const cleanUrl = new URL(window.location.href)
      cleanUrl.searchParams.delete('saved')
      window.history.replaceState(window.history.state, '', cleanUrl.toString())
    } catch {
      // Network/auth errors fall through; toast is owned by useSavedSearches.
    }
  }

  // "Hide covers" toggle — persisted in localStorage for visual sensitivity.
  // When no localStorage value exists, seed from Save-Data / 2g effectiveType
  // so mobile-data patrons aren't forced to discover the setting first.
  // Readers'-advisory shelf banner: surfaced when /catalog is opened with
  // ?shelf=<slug> (e.g. from the /discover chip row). Reads the URL directly
  // -- the catalog page state hook owns search/filter params but does not
  // gate non-filter URL keys.
  const [shelfSlug, setShelfSlug] = useState<string | null>(() => {
    if (typeof window === 'undefined') return null
    return new URLSearchParams(window.location.search).get('shelf')
  })
  const clearShelf = () => {
    setShelfSlug(null)
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href)
      url.searchParams.delete('shelf')
      window.history.replaceState(window.history.state, '', url.toString())
    }
  }

  const [hideCoversInit] = useState(getInitialHideCovers)
  const [hideCovers, setHideCovers] = useState(hideCoversInit.value)
  const [dataSaverNoticeDismissed, setDataSaverNoticeDismissed] = useState(false)
  const toggleHideCovers = () => {
    setHideCovers((prev) => {
      const next = !prev
      try { localStorage.setItem('catalog-hide-covers', String(next)) } catch { /* ignore: localStorage may be unavailable */ }
      return next
    })
    // Explicit toggle is now the patron's choice; banner is no longer relevant.
    setDataSaverNoticeDismissed(true)
  }
  const showDataSaverNotice = hideCoversInit.autoApplied && hideCovers && !dataSaverNoticeDismissed
  const handleShowCoversFromNotice = () => {
    setHideCovers(false)
    try { localStorage.setItem('catalog-hide-covers', 'false') } catch { /* ignore: localStorage may be unavailable */ }
    setDataSaverNoticeDismissed(true)
  }
  const resetCoversToDefault = () => {
    setHideCovers(false)
    try { localStorage.setItem('catalog-hide-covers', 'false') } catch { /* ignore: localStorage may be unavailable */ }
  }
  const resolvedShowImages = effectiveShowImages && !hideCovers
  const resolvedViewMode = hideCovers ? 'list' as const : viewMode
  const resolvedGridDisabled = isGridDisabled || hideCovers

  // Announce filter chip add/remove for screen readers. The general results
  // live region only reports counts; this tells the user which filter changed.
  // Uses the "store info from previous renders" pattern (setState during render
  // when an input changes) instead of useEffect, per react-hooks/set-state-in-effect.
  const [prevChipsKey, setPrevChipsKey] = useState('')
  const [filterAnnouncement, setFilterAnnouncement] = useState('')
  const currentChipLabels = activeFilterChips.map((c) => c.label)
  const currentChipsKey = currentChipLabels.join('|')
  if (currentChipsKey !== prevChipsKey) {
    setPrevChipsKey(currentChipsKey)
    const previous = prevChipsKey ? prevChipsKey.split('|') : []
    const added = currentChipLabels.filter((label) => !previous.includes(label))
    const removed = previous.filter((label) => !currentChipLabels.includes(label))
    const messages: string[] = []
    if (currentChipLabels.length === 0 && previous.length > 0) {
      messages.push(t('catalog.filterAnnouncements.allCleared', 'All filters cleared.'))
    } else {
      added.forEach((label) =>
        messages.push(t('catalog.filterAnnouncements.added', '{{label}} filter added.').replace('{{label}}', label)),
      )
      removed.forEach((label) =>
        messages.push(t('catalog.filterAnnouncements.removed', '{{label}} filter removed.').replace('{{label}}', label)),
      )
    }
    if (messages.length > 0) setFilterAnnouncement(messages.join(' '))
  }

  return (
    <div className={clsx('bg-lsc-cream dark:bg-lsc-dark min-h-screen', focusMode && 'focus-deep-dive')}>

      <h1 className="sr-only">{t('catalog.title', 'Browse the Catalog')}</h1>

      {/* Sticky search bar */}
      <CatalogSearchBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onSubmit={handleSearch}
        onClearSearch={handleClearSearch}
        suggestions={suggestions}
        showSuggestions={showSuggestions}
        onShowSuggestionsChange={setShowSuggestions}
        selectedSuggestionIndex={selectedSuggestionIndex}
        onSelectedSuggestionIndexChange={setSelectedSuggestionIndex}
        onSuggestionSelect={handleSelectSuggestion}
        searchInputRef={searchInputRef}
        suggestionsRef={suggestionsRef}
        isLoading={isLoading}
        reduceMotion={reduceMotion}
      />

      {/* Screen reader live region for result counts */}
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {isLoading
          ? t('catalog.loadingResults')
          : data && (activeQuery || hasActiveFilters)
            ? getGentleResultsMessage(data.total, hasActiveFilters, t)
            : ''}
      </div>

      {/* Screen reader live region for filter add/remove */}
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {filterAnnouncement}
      </div>

      {showDataSaverNotice && (
        <div className="max-w-[1200px] mx-auto px-6 pt-4">
          <div
            className="flex items-center gap-3 px-4 py-3 mb-4 rounded-xl bg-lsc-cream dark:bg-earth-800 border border-lsc-border dark:border-earth-700"
            role="status"
          >
            <p className="text-sm text-lsc-dark dark:text-lsc-cream flex-1">
              {t('catalog.dataSaver.message')}
            </p>
            <button
              onClick={handleShowCoversFromNotice}
              className="px-3 py-1.5 text-sm font-semibold bg-lsc-dark dark:bg-lsc-cream text-white dark:text-lsc-dark rounded-lg hover:bg-lsc-dark/80 dark:hover:bg-lsc-cream/80 flex-shrink-0"
            >
              {t('catalog.dataSaver.showCovers')}
            </button>
            <button
              onClick={() => setDataSaverNoticeDismissed(true)}
              className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/50 hover:text-lsc-dark dark:hover:text-lsc-cream flex-shrink-0"
              aria-label={t('catalog.dataSaver.dismiss')}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Sidebar + Results flex layout */}
      <div className="flex max-w-[1200px] mx-auto px-6 py-6 gap-8 overflow-x-hidden">

        {/* Sidebar */}
        <CatalogFilterSidebar
          filters={{
            item_type: filters.item_type,
            location: filters.location,
            publisher: filters.publisher,
            reading_time: filters.reading_time,
            access: filters.access,
            topic: filters.topic,
            language: filters.language,
            year_min: filters.year_min,
            year_max: filters.year_max,
          }}
          showNewArrivals={showNewArrivals}
          showLargePrintOnly={showLargePrintOnly}
          availableNowOnly={filters.available_only}
          availableForHold={filters.available_for_hold}
          onFilterChange={handleFacetSelect}
          onToggleNewArrivals={() => setShowNewArrivals(prev => !prev)}
          onToggleLargePrint={() => setShowLargePrintOnly(prev => !prev)}
          onToggleAvailableNow={() => {
            handleFacetSelect('available_only', filters.available_only ? '' : 'true')
          }}
          onToggleAvailableForHold={() => {
            handleFacetSelect('available_for_hold', filters.available_for_hold ? '' : 'true')
          }}
          onClearFilters={handleClearFilters}
          isDrawerOpen={isDrawerOpen}
          onDrawerClose={() => setIsDrawerOpen(false)}
          minLexile={filters.min_lexile}
          maxLexile={filters.max_lexile}
          onLexileChange={handleLexileChange}
          facets={data?.facets}
          subjectFacetSelections={filters.subject_facets ?? []}
          onSubjectFacetsChange={onSubjectFacetsChange}
          authorFacetSelections={filters.author_facets ?? []}
          onAuthorFacetsChange={onAuthorFacetsChange}
          seriesFacetSelections={filters.series_facets ?? []}
          onSeriesFacetsChange={onSeriesFacetsChange}
          announceToScreenReader={setFilterAnnouncement}
          onClearSearchHistory={() => {
            try { localStorage.removeItem(SEARCH_PREFS_KEY) } catch { /* localStorage unavailable */ }
            handleClearFilters()
            setFilterAnnouncement(t('catalog.facets.privacyNote', 'Your selections stay on this device only.'))
          }}
        />

        {/* Results area */}
        <main className="flex-1 min-w-0" id="results-top" ref={resultsRef}>

          {/* Readers'-advisory shelf banner -- only when ?shelf= present */}
          {shelfSlug && <ShelfBanner slug={shelfSlug} onClear={clearShelf} />}

          {/* Mobile filter button (hidden on lg+) */}
          <MobileFilterButton onClick={() => setIsDrawerOpen(true)} activeCount={activeFilterChips.length} />

          {/* Results bar: count + sort + view toggle */}
          <div className="mb-4 flex flex-col items-start gap-3 lg:flex-row lg:items-center lg:justify-between">
            <span className="text-sm font-bold text-lsc-dark/80 dark:text-lsc-cream/80">
              {data ? formatResultsCount(data.total) : ''}
            </span>
            <div className="flex w-full flex-wrap items-center justify-start gap-2 lg:w-auto lg:justify-end">
              <select
                id="sort-select"
                value={currentSortValue}
                onChange={(e) => handleSortChange(e.target.value)}
                aria-label={t('aria.catalogContent.sortResultsBy')}
                className="max-w-full px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose cursor-pointer"
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {t(option.labelKey)}
                  </option>
                ))}
              </select>
              <CatalogDisplayMenu hideCovers={hideCovers} onToggleHideCovers={toggleHideCovers} onResetCovers={resetCoversToDefault} />
              <CatalogViewToggle viewMode={resolvedViewMode} onViewChange={setViewMode} disabled={resolvedGridDisabled} />
            </div>
          </div>

          {/* Plain-language explainer for the clickable mood tags on the cards.
              Shown on the active browse/search view (where cards render mood
              pills) and out of quiet mode, which hides moods entirely. */}
          {!effectiveQuietMode && (activeQuery || hasActiveFilters) && data && filteredItems.length > 0 && (
            <MoodLegend />
          )}

          {/* Saved searches panel (sits above the filter chips so patrons see
              their saved entries before the active filters of the current run). */}
          {showSavedSearchesUi && (
            <SavedSearchesPanel onRun={handleRunSavedSearch} />
          )}

          {/* Active filter chips */}
          {activeFilterChips.length > 0 && (
            <div className="flex flex-wrap gap-2 items-center mb-4" role="region" aria-label={t('catalog.activeFilters')}>
              {activeFilterChips.map((chip) => (
                <FilterChip
                  key={chip.key}
                  label={chip.label}
                  onRemove={() => handleRemoveChip(chip.key, chip.label)}
                />
              ))}
              <button
                onClick={handleClearFilters}
                className="text-sm text-lsc-rose hover:underline"
              >
                {t('catalog.clearAll')}
              </button>
              {showSavedSearchesUi && (
                <SaveThisSearchButton
                  hasActiveContext={!!activeQuery || hasActiveFilters}
                  snapshot={{
                    query: activeQuery || '',
                    filters: {
                      ...filters,
                      show_new_arrivals: showNewArrivals,
                      show_large_print_only: showLargePrintOnly,
                      sort_direction: sortDirection,
                    },
                    sortBy,
                    viewMode,
                  }}
                />
              )}
            </div>
          )}

          {/* When there are no chips yet but a query is active, still offer
              the save action so a patron can save a bare-query search. */}
          {showSavedSearchesUi && activeFilterChips.length === 0 && (activeQuery || hasActiveFilters) && (
            <div className="mb-4">
              <SaveThisSearchButton
                hasActiveContext={!!activeQuery || hasActiveFilters}
                snapshot={{
                  query: activeQuery || '',
                  filters: {
                    ...filters,
                    show_new_arrivals: showNewArrivals,
                    show_large_print_only: showLargePrintOnly,
                    sort_direction: sortDirection,
                  },
                  sortBy,
                  viewMode,
                }}
              />
            </div>
          )}

          {/* Stopword banner: every token in the query was an FTS stopword,
              so the backend fell through to an unfiltered browse instead of
              returning 0 results. Tell the patron rather than silently
              expanding their search. */}
          {data?.query_was_all_stopwords && activeQuery && (
            <div
              role="status"
              className="mb-4 rounded-lg border border-amber-400/60 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-500/40 px-4 py-3 text-sm text-lsc-dark dark:text-lsc-cream"
              data-testid="catalog-stopword-banner"
            >
              <p className="font-semibold mb-1">
                {t('catalog.stopwordBanner.title', 'That word is too common to search on its own')}
              </p>
              <p>
                {t(
                  'catalog.stopwordBanner.body',
                  'Your search “{{query}}” is a very common English word and our catalog cannot use it on its own. Showing all results instead -- try adding a more specific word like an author, title, or topic.',
                ).replace('{{query}}', activeQuery)}
              </p>
              <button
                type="button"
                onClick={handleClearSearch}
                className="mt-2 text-sm font-semibold text-lsc-rose hover:underline"
              >
                {t('catalog.stopwordBanner.clear', 'Clear search')}
              </button>
            </div>
          )}

          {/* Results or Loading/Error/Empty states */}
          <CatalogResultsList
            filteredItems={filteredItems}
            viewMode={resolvedViewMode}
            isLoading={isLoading}
            error={error}
            onRetry={refetch}
            data={data}
            activeQuery={activeQuery}
            hasActiveFilters={hasActiveFilters}
            effectiveQuietMode={effectiveQuietMode}
            effectiveSimplifiedView={effectiveSimplifiedView}
            effectiveShowImages={resolvedShowImages}
            speakingItemId={speakingItemId}
            onSpeak={handleSpeak}
            onStopSpeak={handleStopSpeak}
            shouldVirtualize={shouldVirtualize}
            virtualizer={virtualizer}
            virtualScrollRef={virtualScrollRef}
            preferPagination={preferPagination}
            currentPage={currentPage}
            onPageChange={handlePageChange}
            didYouMean={didYouMean}
            onDidYouMeanClick={handleDidYouMeanClick}
            onClearFilters={handleClearFilters}
            onBrowseFormat={handleBrowseFormat}
            shelfStatusMap={shelfStatusMap}
            availabilityMap={availabilityMap}
            challengedItemIds={challengedItemIds}
            languageFilter={filters.language}
            currentUserRole={user?.role}
          />

          {/* Landing state: no query, no filters */}
          {!activeQuery && !hasActiveFilters && !isLoading && (
            <CatalogLandingPanel
              filteredItems={filteredItems}
              activeFormat={filters.item_type}
              onBrowseFormat={handleBrowseFormat}
              effectiveQuietMode={effectiveQuietMode}
              effectiveSimplifiedView={effectiveSimplifiedView}
              effectiveShowImages={resolvedShowImages}
              speakingItemId={speakingItemId}
              onSpeak={handleSpeak}
              onStopSpeak={handleStopSpeak}
              viewMode={resolvedViewMode}
              readingLists={readingLists}
              hasData={!!data}
            />
          )}
        </main>
      </div>
    </div>
  )
}
