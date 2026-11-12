/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { useTranslation } from '@/i18n'
import { clean } from '@/lib/utils'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search,
  Sparkles,
  Users,
  Gem,
  Loader2,
  Brain,
  Zap,
  Globe,
  ArrowRight,
  X,
  AlertCircle,
  Settings,
} from 'lucide-react'
import {
  semanticSearch,
  hybridSearch,
  crossCollectionSearch,
  autocomplete,
  findSimilarAuthors,
  getHiddenGems,
  findSimilarItems,
  getSemanticHealth,
  type SemanticSearchResult,
  type AutocompleteSuggestion,
  type SimilarAuthor,
  type HiddenGemResult,
  type CrossCollectionResponse,
} from '@/api/domains/catalog/semantic-search-api'
import { clsx } from '@/utils/helpers'
import type { SearchMode, SearchModeConfig } from '../components/catalog/semantic-search/types'
import { EXAMPLE_QUERIES } from '../components/catalog/semantic-search/semantic-search-data'
import { SearchResultCard } from '../components/catalog/semantic-search/SearchResultCard'
import { HiddenGemCard } from '../components/catalog/semantic-search/HiddenGemCard'
import { SimilarAuthorCard } from '../components/catalog/semantic-search/SimilarAuthorCard'
import { AutocompleteDropdown } from '../components/catalog/semantic-search/AutocompleteDropdown'
import {
  SemanticHealthBanner,
  SearchMetaBar,
  HybridWeightSlider,
  CollectionFilter,
} from '../components/catalog/semantic-search/SearchControls'
import PageContainer from '@/components/layout/PageContainer'

const AUTOCOMPLETE_DEBOUNCE_MS = 150

// eslint-disable-next-line complexity
export default function SemanticSearchPage() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [mode, setMode] = useState<SearchMode>('hybrid')

  const SEARCH_MODES: SearchModeConfig[] = useMemo(() => [
    {
      id: 'hybrid',
      label: 'Hybrid',
      description: 'AI + keyword. Best for most searches.',
      icon: Zap,
      color: 'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300',
      activeColor: 'bg-lsc-rose text-white',
    },
    {
      id: 'semantic',
      label: 'AI Search',
      description: 'Natural language. Describe what you want.',
      icon: Sparkles,
      color: 'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300',
      activeColor: 'bg-category-600 text-white',
    },
    {
      id: 'cross-collection',
      label: 'Cross-Collection',
      description: 'Search local, Palace, & Gutenberg together.',
      icon: Globe,
      color: 'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300',
      activeColor: 'bg-emerald-600 text-white',
    },
    {
      id: 'hidden-gems',
      label: 'Hidden Gems',
      description: 'Discover underrated, overlooked books.',
      icon: Gem,
      color: 'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300',
      activeColor: 'bg-status-warning-600 text-white',
    },
    {
      id: 'similar-authors',
      label: 'Similar Authors',
      description: 'Find authors like your favorites.',
      icon: Users,
      color: 'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300',
      activeColor: 'bg-rose-600 text-white',
    },
  // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [t])

  const [query, setQuery] = useState('')
  const [authorQuery, setAuthorQuery] = useState('')
  const [gemSubject, setGemSubject] = useState('')
  const [gemSource, setGemSource] = useState('')

  const [results, setResults] = useState<SemanticSearchResult[]>([])
  const [gems, setGems] = useState<HiddenGemResult[]>([])
  const [similarAuthors, setSimilarAuthors] = useState<SimilarAuthor[]>([])
  const [crossData, setCrossData] = useState<CrossCollectionResponse | null>(null)

  const [searchTime, setSearchTime] = useState<number | null>(null)
  const [totalResults, setTotalResults] = useState(0)
  const [wasCached, setWasCached] = useState(false)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [showOptions, setShowOptions] = useState(false)

  const [suggestions, setSuggestions] = useState<AutocompleteSuggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [autocompleteLoading, setAutocompleteLoading] = useState(false)

  const [semanticWeight, setSemanticWeight] = useState(0.6)
  const [selectedSources, setSelectedSources] = useState<string[]>(['local', 'gutenberg', 'palace'])
  const [minSimilarity, setMinSimilarity] = useState(0.3)
  const [filtersDirty, setFiltersDirty] = useState(false)

  const DEFAULT_SEMANTIC_WEIGHT = 0.6
  const DEFAULT_MIN_SIMILARITY = 0.3
  const DEFAULT_SOURCES_COUNT = 3
  const hasNonDefaultOptions =
    semanticWeight !== DEFAULT_SEMANTIC_WEIGHT ||
    minSimilarity !== DEFAULT_MIN_SIMILARITY ||
    selectedSources.length !== DEFAULT_SOURCES_COUNT ||
    gemSource !== ''

  const searchInputRef = useRef<HTMLDivElement>(null)
  const autocompleteTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const resultsRef = useRef<HTMLDivElement>(null)
  const hasInitializedFromUrl = useRef(false)

  const { data: health } = useQuery({
    queryKey: ['semantic-health'],
    queryFn: getSemanticHealth,
    staleTime: 1000 * 60 * 2,
    refetchInterval: 1000 * 60 * 5,
  })

  const handleAutocomplete = useCallback(async (value: string) => {
    if (value.length < 2) {
      setSuggestions([])
      setShowSuggestions(false)
      setAutocompleteLoading(false)
      return
    }
    try {
      const result = await autocomplete({ query: value, limit: 8 })
      setSuggestions(result.suggestions)
      setShowSuggestions(result.suggestions.length > 0)
    } catch {
      setSuggestions([])
    } finally {
      setAutocompleteLoading(false)
    }
  }, [])

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value
      setQuery(value)
      if (autocompleteTimerRef.current) clearTimeout(autocompleteTimerRef.current)
      if (value.length >= 2) {
        setAutocompleteLoading(true)
        setShowSuggestions(true)
      } else {
        setAutocompleteLoading(false)
        setShowSuggestions(false)
      }
      autocompleteTimerRef.current = setTimeout(() => {
        handleAutocomplete(value)
      }, AUTOCOMPLETE_DEBOUNCE_MS)
    },
    [handleAutocomplete]
  )

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchInputRef.current && !searchInputRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const executeSearch = useCallback(async (overrideQuery?: string) => {
    setShowSuggestions(false)
    setError(null)
    setHasSearched(true)
    setFiltersDirty(false)

    if (mode === 'hidden-gems') {
      setLoading(true)
      try {
        const result = await getHiddenGems(clean({
          subject: gemSubject || undefined,
          source: gemSource || undefined,
          limit: 24,
          minScore: 0.3,
        }))
        setGems(result.gems)
        setTotalResults(result.total)
        setSearchTime(result.search_time_ms)
        setResults([])
        setSimilarAuthors([])
        setCrossData(null)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to discover hidden gems')
      } finally {
        setLoading(false)
      }
      return
    }

    if (mode === 'similar-authors') {
      const authorName = authorQuery.trim() || query.trim()
      if (!authorName) return
      setLoading(true)
      try {
        const result = await findSimilarAuthors(authorName, 12)
        setSimilarAuthors(result.similar_authors)
        setTotalResults(result.similar_authors.length)
        setSearchTime(result.search_time_ms)
        setResults([])
        setGems([])
        setCrossData(null)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to find similar authors')
      } finally {
        setLoading(false)
      }
      return
    }

    const trimmedQuery = (overrideQuery ?? query).trim()
    if (!trimmedQuery) return

    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('q', trimmedQuery)
    setSearchParams(nextParams, { replace: true })

    setLoading(true)
    try {
      if (mode === 'cross-collection') {
        const result = await crossCollectionSearch(trimmedQuery, 30)
        setCrossData(result)
        setResults(result.results)
        setTotalResults(result.total_results)
        setSearchTime(result.search_time_ms)
        setWasCached(result.was_cached)
        setGems([])
        setSimilarAuthors([])
      } else if (mode === 'semantic') {
        const result = await semanticSearch(clean({
          query: trimmedQuery,
          limit: 30,
          sources: selectedSources.length < 3 ? selectedSources : undefined,
          minSimilarity,
        }))
        setResults(result.results)
        setTotalResults(result.total_results)
        setSearchTime(result.search_time_ms)
        setWasCached(result.was_cached)
        setGems([])
        setSimilarAuthors([])
        setCrossData(null)
      } else {
        const result = await hybridSearch(clean({
          query: trimmedQuery,
          limit: 30,
          semanticWeight,
          keywordWeight: 1 - semanticWeight,
          sources: selectedSources.length < 3 ? selectedSources : undefined,
        }))
        setResults(result.merged_results)
        setTotalResults(result.total_results)
        setSearchTime(result.search_time_ms)
        setWasCached(false)
        setGems([])
        setSimilarAuthors([])
        setCrossData(null)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed')
    } finally {
      setLoading(false)
    }

    setTimeout(() => {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 150)
  }, [
    mode,
    query,
    authorQuery,
    gemSubject,
    gemSource,
    semanticWeight,
    selectedSources,
    minSimilarity,
    searchParams,
    setSearchParams,
  ])

  useEffect(() => {
    if (hasInitializedFromUrl.current) return

    const initialQuery = searchParams.get('q')?.trim()
    if (!initialQuery) {
      hasInitializedFromUrl.current = true
      return
    }

    hasInitializedFromUrl.current = true
    setQuery(initialQuery)
    setTimeout(() => {
      void executeSearch(initialQuery)
    }, 0)
  }, [searchParams, executeSearch])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') executeSearch()
      if (e.key === 'Escape') setShowSuggestions(false)
    },
    [executeSearch]
  )

  const handleSuggestionSelect = useCallback(
    (suggestion: AutocompleteSuggestion) => {
      setQuery(suggestion.title)
      setShowSuggestions(false)
      setTimeout(() => executeSearch(), 50)
    },
    [executeSearch]
  )

  const handleFindSimilar = useCallback(async (result: SemanticSearchResult) => {
    setLoading(true)
    setError(null)
    try {
      const similar = await findSimilarItems(result.source, result.source_id, 12)
      setResults(similar.similar_items)
      setTotalResults(similar.similar_items.length)
      setSearchTime(similar.search_time_ms)
      setQuery(`Similar to: ${result.title}`)
      setHasSearched(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to find similar items')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleAuthorExplore = useCallback((author: string) => {
    setMode('similar-authors')
    setAuthorQuery(author)
    setResults([])
    setGems([])
    setSimilarAuthors([])
    setSearchTime(null)
    setHasSearched(false)
  }, [])

  const handleModeChange = useCallback((newMode: SearchMode) => {
    setMode(newMode)
    setResults([])
    setGems([])
    setSimilarAuthors([])
    setCrossData(null)
    setSearchTime(null)
    setError(null)
    setHasSearched(false)
  }, [])

  const handleExampleQuery = useCallback(
    (example: string) => {
      if (mode === 'similar-authors') {
        setAuthorQuery(example)
      } else if (mode === 'hidden-gems') {
        setGemSubject(example)
      } else {
        setQuery(example)
      }
    },
    [mode]
  )

  const currentMode = SEARCH_MODES.find((m) => m.id === mode)!
  const ModeIcon = currentMode.icon
  const hasResults = results.length > 0 || gems.length > 0 || similarAuthors.length > 0

  return (
    <PageContainer className="py-8">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-gradient-to-br from-lsc-rose to-category-600 rounded-xl">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              AI-Powered Discovery
            </h1>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Search by meaning, discover hidden gems, and explore author connections
            </p>
          </div>
        </div>

        {health && <SemanticHealthBanner health={health} />}

        {!health?.semantic_search_ready && health && (
          <div className="flex flex-wrap gap-2 mt-3">
            {Object.entries(health.features).map(([feature, ready]) => (
              <span
                key={feature}
                className={clsx(
                  'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border',
                  ready
                    ? 'bg-status-success-50 text-status-success-700 border-status-success-200 dark:bg-status-success-900/20 dark:text-status-success-300 dark:border-status-success-800'
                    : 'bg-earth-50 text-earth-600 border-lsc-border dark:bg-earth-700 dark:text-earth-300 dark:border-earth-700'
                )}
              >
                {ready ? '✓' : '○'} {feature.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2 mb-5">
        {SEARCH_MODES.map((m) => {
          const Icon = m.icon
          const isActive = mode === m.id
          return (
            <button
              key={m.id}
              onClick={() => handleModeChange(m.id)}
              title={m.description}
              className={clsx(
                'flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-medium transition-all shadow-sm',
                isActive ? m.activeColor + ' shadow-md' : m.color + ' hover:shadow'
              )}
              aria-pressed={isActive}
            >
              <Icon className="w-3.5 h-3.5" />
              {m.label}
            </button>
          )
        })}
      </div>

      <div className="mb-4 px-3 py-2 bg-earth-50 dark:bg-earth-700/30 border-l-2 border-lsc-border dark:border-earth-600 rounded-r-lg flex items-center gap-2">
        <ModeIcon className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0" />
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <span className="font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{currentMode.label}:</span>{' '}
          {currentMode.description}
        </p>
      </div>

      <div className="relative mb-4" ref={searchInputRef}>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <div className="absolute left-3 top-1/2 -translate-y-1/2">
              {loading ? (
                <Loader2 className="w-5 h-5 text-lsc-rose motion-safe:animate-spin" />
              ) : (
                <Search className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              )}
            </div>

            {(mode === 'semantic' || mode === 'hybrid' || mode === 'cross-collection') && (
              <input
                type="text"
                value={query}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder={
                  mode === 'semantic'
                    ? 'Describe what you want, e.g. "books about grief and healing"'
                    : mode === 'cross-collection'
                    ? 'Search all collections — local catalog and Gutenberg'
                    : 'Search by title, author, topic, or concept...'
                }
                className="w-full pl-10 pr-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose bg-lsc-white dark:bg-earth-800 dark:text-earth-100 text-sm"
                role="combobox"
                aria-label={t('aria.federated-search.searchQuery')}
                aria-autocomplete="list"
                aria-controls="autocomplete-list"
                aria-expanded={showSuggestions}
              />
            )}

            {mode === 'similar-authors' && (
              <input
                type="text"
                value={authorQuery}
                onChange={(e) => setAuthorQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder='Enter an author name, e.g. "Isaac Asimov" or "Ursula K. Le Guin"'
                className="w-full pl-10 pr-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl focus:ring-2 focus:ring-rose-500 focus:border-rose-500 bg-lsc-white dark:bg-earth-800 dark:text-earth-100 text-sm"
                aria-label={t('aria.semanticSearch.authorName')}
              />
            )}

            {mode === 'hidden-gems' && (
              <input
                type="text"
                value={gemSubject}
                onChange={(e) => setGemSubject(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder='Filter by subject, e.g. "science fiction" — or leave blank for all genres'
                className="w-full pl-10 pr-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl focus:ring-2 focus:ring-status-warning-500 focus:border-status-warning-500 bg-lsc-white dark:bg-earth-800 dark:text-earth-100 text-sm"
                aria-label={t('aria.semanticSearch.subjectFilter')}
              />
            )}
          </div>

          <button
            onClick={() => executeSearch()}
            disabled={loading}
            aria-busy={loading}
            className={clsx(
              'px-5 py-3 rounded-xl text-white text-sm font-semibold disabled:opacity-50 transition-all shadow-sm hover:shadow-md active:shadow-sm',
              mode === 'hybrid' ? 'bg-lsc-rose hover:bg-lsc-rose/90'
              : mode === 'semantic' ? 'bg-category-600 hover:bg-category-700'
              : mode === 'cross-collection' ? 'bg-emerald-600 hover:bg-emerald-700'
              : mode === 'hidden-gems' ? 'bg-status-warning-600 hover:bg-status-warning-700'
              : 'bg-rose-600 hover:bg-rose-700'
            )}
          >
            {loading ? <><Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" /><span className="sr-only">Loading</span></> : 'Search'}
          </button>

          <button
            onClick={() => setShowOptions(!showOptions)}
            className={clsx(
              'relative px-3 py-3 rounded-xl border text-sm font-medium transition-colors',
              showOptions
                ? 'bg-earth-100 dark:bg-earth-700 border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
                : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-border'
            )}
            aria-expanded={showOptions}
            aria-label={t('aria.semanticSearch.toggleSearchOptions')}
            title={hasNonDefaultOptions ? 'Search options (custom values set)' : 'Search options'}
          >
            <Settings className="w-4 h-4" />
            {hasNonDefaultOptions && (
              <span
                className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-lsc-rose ring-2 ring-white dark:ring-earth-800"
                aria-hidden="true"
              />
            )}
          </button>
        </div>

        <AutocompleteDropdown
          suggestions={suggestions}
          visible={showSuggestions}
          loading={autocompleteLoading}
          onSelect={handleSuggestionSelect}
          onClose={() => setShowSuggestions(false)}
        />
      </div>

      {showOptions && (
        <div className="mb-4 p-4 bg-earth-50 dark:bg-earth-700/30 border border-lsc-border dark:border-earth-700 rounded-xl space-y-4">
          <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Search Options
            {hasSearched && filtersDirty && (
              <span className="ml-auto text-xs font-normal text-status-warning-700 dark:text-status-warning-400">
                (re-search to apply)
              </span>
            )}
          </h3>

          {mode === 'hybrid' && (
            <HybridWeightSlider
              semanticWeight={semanticWeight}
              onChange={(v) => { setSemanticWeight(v); setFiltersDirty(true) }}
            />
          )}

          {(mode === 'semantic' || mode === 'hybrid') && (
            <CollectionFilter
              selected={selectedSources}
              onChange={(v) => { setSelectedSources(v); setFiltersDirty(true) }}
            />
          )}

          {mode === 'semantic' && (
            <div className="flex items-center gap-3">
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">
                Min similarity: {Math.round(minSimilarity * 100)}%
              </span>
              <input
                type="range"
                min={0}
                max={0.9}
                step={0.05}
                value={minSimilarity}
                onChange={(e) => { setMinSimilarity(parseFloat(e.target.value)); setFiltersDirty(true) }}
                className="flex-1 h-1.5 accent-category-600"
                aria-label={t('aria.semanticSearch.minimumSimilarityThreshold')}
              />
            </div>
          )}

          {mode === 'hidden-gems' && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Source:</span>
              {['', 'local', 'gutenberg'].map((src) => (
                <button
                  key={src || 'all'}
                  onClick={() => setGemSource(src)}
                  className={clsx(
                    'px-2.5 py-1 rounded-full text-xs font-medium border transition-colors',
                    gemSource === src
                      ? 'bg-status-warning-600 text-white border-status-warning-600'
                      : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border-lsc-border dark:border-earth-700 hover:border-status-warning-300'
                  )}
                >
                  {src === '' ? 'All Sources' : src === 'local' ? 'Library Catalog' : 'Gutenberg'}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {!hasSearched && (
        <div className="mb-6">
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Try an example:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUERIES[mode].map((ex) => (
              <button
                key={ex}
                onClick={() => handleExampleQuery(ex)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose/30 dark:hover:border-lsc-rose/30 rounded-full text-xs text-lsc-dark/70 dark:text-lsc-cream/70 transition-colors"
              >
                <ArrowRight className="w-3 h-3 text-lsc-dark/70 dark:text-lsc-cream/70" />
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-status-danger-700 dark:text-status-danger-300">Search Error</p>
            <p className="text-xs text-status-danger-600 dark:text-status-danger-400 mt-0.5">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            aria-label={t('aria.dismissError', 'Dismiss error')}
            className="ml-auto p-1 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/40 rounded"
          >
            <X className="w-3.5 h-3.5 text-status-danger-500" />
          </button>
        </div>
      )}

      {searchTime !== null && !loading && (
        <SearchMetaBar
          searchTime={searchTime}
          totalResults={totalResults}
          mode={mode}
          {...(wasCached ? { wasCached } : {})}
          {...(crossData?.source_breakdown ? { crossBreakdown: crossData.source_breakdown } : {})}
          searchModes={SEARCH_MODES}
        />
      )}

      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {loading
          ? 'Searching…'
          : hasSearched && hasResults
            ? `${totalResults} result${totalResults !== 1 ? 's' : ''} found`
            : hasSearched && !hasResults && !error
              ? 'No results found'
              : ''}
      </div>

      <div ref={resultsRef} className="mt-6 space-y-3">
        {loading && (
          <div className="space-y-3 motion-safe:animate-pulse" aria-busy="true" aria-label="Loading search results">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="border border-lsc-border dark:border-earth-700 rounded-xl p-4 flex gap-4">
                <div className="w-16 h-24 bg-earth-200 dark:bg-earth-700 rounded-lg flex-shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-earth-200 dark:bg-earth-700 rounded w-3/4" />
                  <div className="h-3 bg-earth-100 dark:bg-earth-700/50 rounded w-1/3" />
                  <div className="h-3 bg-earth-100 dark:bg-earth-700/50 rounded w-5/6" />
                  <div className="h-3 bg-earth-100 dark:bg-earth-700/50 rounded w-4/6" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && (mode === 'semantic' || mode === 'hybrid' || mode === 'cross-collection') &&
          results.map((result, i) => (
            <SearchResultCard
              key={`${result.id}-${i}`}
              result={result}
              onFindSimilar={handleFindSimilar}
              onAuthorExplore={handleAuthorExplore}
            />
          ))}

        {!loading && mode === 'hidden-gems' && gems.map((gem, i) => (
          <HiddenGemCard key={`gem-${gem.entity_id}-${i}`} gem={gem} />
        ))}

        {!loading && mode === 'similar-authors' && similarAuthors.map((author, i) => (
          <SimilarAuthorCard
            key={`author-${i}`}
            author={author}
            onSearch={(name) => {
              setMode('similar-authors')
              setAuthorQuery(name)
              setSimilarAuthors([])
              setHasSearched(false)
            }}
          />
        ))}

        {!loading && hasSearched && !hasResults && !error && (
          <div className="text-center py-16 text-lsc-dark/70 dark:text-lsc-cream/70">
            <Search className="w-12 h-12 mx-auto mb-4 text-earth-300 dark:text-earth-300" />
            <p className="text-base font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              {mode === 'hidden-gems'
                ? 'No hidden gems found for this topic'
                : mode === 'similar-authors'
                ? 'No similar authors found'
                : 'No results found'}
            </p>
            <p className="text-sm mb-6">
              {mode === 'hidden-gems'
                ? 'Try a broader term, or leave the subject blank to see gems across all genres.'
                : mode === 'similar-authors'
                ? 'Make sure the author name is spelled correctly, or try a different author.'
                : 'Try rephrasing your query, or switch to a different search mode.'}
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => handleModeChange('hybrid')}
                className="px-4 py-2 bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light rounded-lg text-sm hover:bg-lsc-rose/10 dark:hover:bg-lsc-rose/30 transition-colors"
              >
                Try Hybrid Search
              </button>
              <Link
                to="/catalog"
                className="px-4 py-2 bg-earth-50 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg text-sm hover:bg-earth-100 dark:hover:bg-earth-600 transition-colors"
              >
                Browse Catalog
              </Link>
            </div>
          </div>
        )}

        {!loading && !hasSearched && (
          <div className="text-center py-16 text-lsc-dark/70 dark:text-lsc-cream/70">
            <ModeIcon className="w-12 h-12 mx-auto mb-4 opacity-30" />
            <p className="text-sm">
              {mode === 'hidden-gems'
                ? 'Click Search to discover overlooked books with high similarity to popular titles'
                : mode === 'similar-authors'
                ? 'Enter an author name above to find authors with similar writing styles and themes'
                : 'Enter a query above and press Search — or try one of the example queries'}
            </p>
          </div>
        )}
      </div>

      <div className="mt-12 pt-6 border-t border-earth-100 dark:border-earth-800">
        <div className="flex items-center justify-between">
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            AI-powered search
          </p>
          <Link
            to="/staff/admin/semantic-search"
            className="inline-flex items-center gap-1 text-xs text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300"
          >
            <Settings className="w-3 h-3" />
            Embedding Admin
          </Link>
        </div>
      </div>
    </PageContainer>
  )
}
