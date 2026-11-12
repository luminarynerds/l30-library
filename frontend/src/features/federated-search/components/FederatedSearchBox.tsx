/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable prefer-const */
/**
 * FederatedSearchBox Component
 *
 * Search input field with source selection and advanced options
 * Handles query input, suggestions, and search submission
 *
 * Features:
 * - Debounced suggestions (300ms)
 * - Recent search history with localStorage persistence
 * - Popular/trending searches shown when focused but empty
 * - Skeleton loading states
 * - "No suggestions" messaging
 * - Full keyboard navigation (Arrow keys, Enter, Escape)
 * - ARIA accessibility support
 */

import React, { useState, useRef, useEffect } from 'react'
import { Search, X, ChevronDown, Clock, TrendingUp } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import * as api from '../services/federatedSearchApi'
import { useRecentSearches } from '@/hooks/useRecentSearches'
import { SuggestionsSkeleton } from './SuggestionsSkeleton'
import type { SearchSource } from '../types/federated-search.types'
import { t } from '@/i18n'

// ==================== Types ====================

interface FederatedSearchBoxProps {
  /** Initial search query */
  initialQuery?: string
  /** Selected sources */
  selectedSources: SearchSource[]
  /** Called when user submits search */
  onSearch: (query: string, sources: SearchSource[]) => void
  /** Called when sources change */
  onSourcesChange?: (sources: SearchSource[]) => void
  /** Show suggestions */
  showSuggestions?: boolean
  /** Authentication token */
  token?: string
  /** Placeholder text */
  placeholder?: string
  /** CSS class name */
  className?: string
  /** Auto-focus on mount */
  autoFocus?: boolean
}

// ==================== Component ====================

export function FederatedSearchBox({
  initialQuery = '',
  selectedSources,
  onSearch,
  onSourcesChange: _onSourcesChange,
  showSuggestions = true,
  token,
  placeholder = 'Search across multiple sources...',
  className,
  autoFocus = false,
}: FederatedSearchBoxProps): React.ReactElement {
  const [query, setQuery] = useState(initialQuery)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [showSuggestionsDropdown, setShowSuggestionsDropdown] = useState(false)
  const [suggestionsLoading, setSuggestionsLoading] = useState(false)
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1)
  const [popularSearches, setPopularSearches] = useState<string[]>([])
  const [popularLoading, setPopularLoading] = useState(false)
  const [noSuggestionsFound, setNoSuggestionsFound] = useState(false)
  const [isFocused, setIsFocused] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  // Recent searches hook
  const { recentSearches, addRecentSearch, removeRecentSearch } = useRecentSearches()

  // Fetch popular searches on mount
  useEffect(() => {
    const fetchPopular = async () => {
      setPopularLoading(true)
      try {
        const popular = await api.getPopularSearches(5, token)
        setPopularSearches(popular)
      } catch {
        setPopularSearches([])
      } finally {
        setPopularLoading(false)
      }
    }
    fetchPopular()
  }, [token])

  // Fetch suggestions as user types
  useEffect(() => {
    if (!showSuggestions || query.length < 2) {
      setSuggestions([])
      setNoSuggestionsFound(false)
      // Don't hide dropdown if showing recent/popular
      if (query.length === 0 && isFocused) {
        setShowSuggestionsDropdown(true)
      } else {
        setShowSuggestionsDropdown(false)
      }
      return
    }

    let isMounted = true
    let timeoutId: ReturnType<typeof setTimeout>

    const fetchSuggestions = async () => {
      try {
        setSuggestionsLoading(true)
        setNoSuggestionsFound(false)
        const results = await api.getSearchSuggestions(
          query,
          selectedSources.length > 0 ? selectedSources : undefined,
          token
        )
        if (isMounted) {
          setSuggestions(results)
          // Show dropdown even if no results (to display "no suggestions" message)
          setShowSuggestionsDropdown(true)
          setNoSuggestionsFound(results.length === 0)
          setSelectedSuggestionIndex(-1)
        }
      } catch (_error: unknown) {
        if (isMounted) {
          setSuggestions([])
          setNoSuggestionsFound(true)
        }
      } finally {
        if (isMounted) {
          setSuggestionsLoading(false)
        }
      }
    }

    // Debounce suggestions fetch
    timeoutId = setTimeout(fetchSuggestions, 300)

    return () => {
      isMounted = false
      clearTimeout(timeoutId)
    }
  }, [query, selectedSources, showSuggestions, token, isFocused])

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    const items = getNavigableItems()

    if (!showSuggestionsDropdown || items.length === 0) {
      if (e.key === 'Enter') {
        e.preventDefault()
        handleSubmit()
      }
      return
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedSuggestionIndex((prev: number) =>
          prev < items.length - 1 ? prev + 1 : 0
        )
        break

      case 'ArrowUp':
        e.preventDefault()
        setSelectedSuggestionIndex((prev: number) =>
          prev > 0 ? prev - 1 : items.length - 1
        )
        break

      case 'Enter':
        e.preventDefault()
        if (selectedSuggestionIndex >= 0 && items[selectedSuggestionIndex]) {
          const selected = items[selectedSuggestionIndex]
          handleSuggestionSelect(selected)
          setSelectedSuggestionIndex(-1)
        } else {
          handleSubmit()
        }
        break

      case 'Escape':
        e.preventDefault()
        setShowSuggestionsDropdown(false)
        break

      default:
        break
    }
  }

  const handleSubmit = () => {
    if (query.trim()) {
      addRecentSearch(query.trim())
      onSearch(query.trim(), selectedSources)
      setShowSuggestionsDropdown(false)
    }
  }

  const handleClear = () => {
    setQuery('')
    setSuggestions([])
    setNoSuggestionsFound(false)
    setShowSuggestionsDropdown(false)
    inputRef.current?.focus()
  }

  const handleFocus = () => {
    setIsFocused(true)
    if (query.length === 0 && (recentSearches.length > 0 || popularSearches.length > 0)) {
      setShowSuggestionsDropdown(true)
    } else if (query.length >= 2 && (suggestions.length > 0 || noSuggestionsFound)) {
      setShowSuggestionsDropdown(true)
    }
  }

  const handleBlur = () => {
    setTimeout(() => {
      setIsFocused(false)
      setShowSuggestionsDropdown(false)
    }, 200)
  }

  const handleSuggestionSelect = (suggestion: string) => {
    setQuery(suggestion)
    addRecentSearch(suggestion)
    setShowSuggestionsDropdown(false)
    onSearch(suggestion, selectedSources)
  }

  // Determine what to show in dropdown
  const showRecentAndPopular = query.length === 0 && isFocused
  const showSuggestionsList = query.length >= 2 && suggestions.length > 0
  const showNoSuggestions = query.length >= 2 && noSuggestionsFound && !suggestionsLoading

  // Get all items for keyboard navigation
  const getNavigableItems = (): string[] => {
    if (showRecentAndPopular) {
      return [...recentSearches.map(s => s.query), ...popularSearches]
    }
    return suggestions
  }

  return (
    <div className={clsx('space-y-2', className)}>
      {/* Search Input */}
      <div className="relative">
        <form onSubmit={(e) => { e.preventDefault(); handleSubmit() }} className="relative">
          <div className="relative flex items-center">
            {/* Search Icon */}
            <Search className="absolute left-3 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 pointer-events-none" aria-hidden="true" />

            {/* Input Field */}
            <input
              ref={inputRef}
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={handleFocus}
              onBlur={handleBlur}
              placeholder={placeholder}
              autoFocus={autoFocus}
              className={clsx(
                'w-full pl-10 pr-10 py-3 rounded-lg border-2 transition-all',
                'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream',
                'border-lsc-border dark:border-earth-700',
                'focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent',
                'placeholder:text-lsc-dark/70 dark:text-lsc-cream/70 dark:placeholder:text-earth-400'
              )}
              aria-label={t('aria.federated-search.searchQuery')}
              aria-autocomplete="list"
              aria-controls={showSuggestionsDropdown ? 'search-suggestions' : undefined}
              aria-expanded={showSuggestionsDropdown}
              aria-activedescendant={
                selectedSuggestionIndex >= 0
                  ? `suggestion-${selectedSuggestionIndex}`
                  : undefined
              }
            />

            {/* Clear Button */}
            {query && (
              <button
                type="button"
                onClick={handleClear}
                className="absolute right-3 p-1 text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose rounded"
                aria-label={t('aria.federated-search.clearSearchQuery')}
              >
                <X className="w-5 h-5" aria-hidden="true" />
              </button>
            )}
          </div>

          {/* Search Button (hidden but functional for form submission) */}
          <button type="submit" className="hidden" aria-hidden="true" />
        </form>

        {/* Suggestions Dropdown */}
        {showSuggestionsDropdown && (
          <div
            ref={suggestionsRef}
            id="search-suggestions"
            className="absolute top-full left-0 right-0 mt-1 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg shadow-lg z-10 overflow-hidden"
            role="listbox"
          >
            {/* Skeleton loading state */}
            {suggestionsLoading && query.length >= 2 && (
              <SuggestionsSkeleton count={4} />
            )}

            {/* Recent & Popular searches (when input is empty) */}
            {showRecentAndPopular && !suggestionsLoading && (
              <>
                {/* Recent Searches */}
                {recentSearches.length > 0 && (
                  <div>
                    <div className="px-4 py-2 text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                      <span>
                        <Clock className="w-3 h-3 inline-block mr-1.5 -mt-0.5" aria-hidden="true" />
                        Recent Searches
                      </span>
                      <span className="normal-case font-normal text-earth-600 dark:text-earth-600" title="Search history is stored only in your browser and never sent to our servers">
                        Stored locally
                      </span>
                    </div>
                    {recentSearches.slice(0, 5).map((search, index) => (
                      <div
                        key={`recent-${search.query}`}
                        id={`suggestion-${index}`}
                        tabIndex={-1}
                        onClick={() => handleSuggestionSelect(search.query)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            handleSuggestionSelect(search.query)
                          }
                        }}
                        onMouseEnter={() => setSelectedSuggestionIndex(index)}
                        className={clsx(
                          'w-full text-left px-4 py-2 text-sm transition-colors flex items-center justify-between group cursor-pointer',
                          'focus:outline-none focus:ring-2 focus:ring-inset focus:ring-lsc-rose',
                          index === selectedSuggestionIndex
                            ? 'bg-earth-100 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream'
                            : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700'
                        )}
                        role="option"
                        aria-selected={index === selectedSuggestionIndex}
                      >
                        <span>
                          <Clock className="w-3 h-3 inline-block mr-2 opacity-50" aria-hidden="true" />
                          {search.query}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            removeRecentSearch(search.query)
                          }}
                          className="opacity-0 group-hover:opacity-100 focus:opacity-100 p-1 hover:text-status-danger-500 transition-opacity"
                          aria-label={`Remove "${search.query}" from recent searches`}
                        >
                          <X className="w-3 h-3" aria-hidden="true" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Popular/Trending Searches */}
                {popularSearches.length > 0 && (
                  <div>
                    <div className="px-4 py-2 text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider border-b border-lsc-border dark:border-earth-700">
                      <TrendingUp className="w-3 h-3 inline-block mr-1.5 -mt-0.5" aria-hidden="true" />
                      Trending
                    </div>
                    {popularSearches.map((search: string, i: number) => {
                      const index = recentSearches.length + i
                      return (
                        <button
                          key={`popular-${search}`}
                          id={`suggestion-${index}`}
                          tabIndex={-1}
                          onClick={() => handleSuggestionSelect(search)}
                          onMouseEnter={() => setSelectedSuggestionIndex(index)}
                          className={clsx(
                            'w-full text-left px-4 py-2 text-sm transition-colors',
                            'focus:outline-none focus:ring-2 focus:ring-inset focus:ring-lsc-rose',
                            index === selectedSuggestionIndex
                              ? 'bg-earth-100 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream'
                              : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700'
                          )}
                          role="option"
                          aria-selected={index === selectedSuggestionIndex}
                        >
                          <TrendingUp className="w-3 h-3 inline-block mr-2 opacity-50" aria-hidden="true" />
                          {search}
                        </button>
                      )
                    })}
                  </div>
                )}

                {/* Loading popular searches */}
                {popularLoading && recentSearches.length === 0 && (
                  <SuggestionsSkeleton count={3} />
                )}

                {/* Empty state when no recent or popular */}
                {!popularLoading && recentSearches.length === 0 && popularSearches.length === 0 && (
                  <div className="p-4 text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Start typing to search...
                  </div>
                )}
              </>
            )}

            {/* Suggestions list (when typing) */}
            {showSuggestionsList && !suggestionsLoading && suggestions.map((suggestion: string, index: number) => (
              <button
                key={index}
                id={`suggestion-${index}`}
                tabIndex={-1}
                onClick={() => handleSuggestionSelect(suggestion)}
                onMouseEnter={() => setSelectedSuggestionIndex(index)}
                className={clsx(
                  'w-full text-left px-4 py-2 text-sm transition-colors',
                  'focus:outline-none focus:ring-2 focus:ring-inset focus:ring-lsc-rose',
                  index === selectedSuggestionIndex
                    ? 'bg-earth-100 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream'
                    : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700'
                )}
                role="option"
                aria-selected={index === selectedSuggestionIndex}
              >
                <Search className="w-3 h-3 inline-block mr-2 opacity-50" aria-hidden="true" />
                {suggestion}
              </button>
            ))}

            {/* No suggestions message */}
            {showNoSuggestions && (
              <div className="p-4 text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <Search className="w-5 h-5 mx-auto mb-2 opacity-40" aria-hidden="true" />
                <p>No suggestions for "{query}"</p>
                <p className="text-xs mt-1">Press Enter to search anyway</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Source Selection */}
      <details className="text-sm">
        <summary className="cursor-pointer px-3 py-2 rounded-lg hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-800 flex items-center justify-between">
          <span className="font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
            {selectedSources.length === 0
              ? 'Select sources'
              : `${selectedSources.length} source${selectedSources.length === 1 ? '' : 's'} selected`}
          </span>
          <ChevronDown className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 transition-transform group-open:rotate-180" aria-hidden="true" />
        </summary>

        {/* Note: Source selector should be implemented separately and integrated here */}
        <div className="mt-2 p-3 bg-earth-50 dark:bg-earth-800/50 rounded-lg border border-lsc-border dark:border-earth-700 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          <p>Source selection component should be integrated here</p>
        </div>
      </details>

      {/* Query Info */}
      {query && (
        <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 px-3">
          Press <kbd className="px-2 py-1 rounded bg-earth-200 dark:bg-earth-700">Enter</kbd> to search
        </div>
      )}
    </div>
  )
}

export default FederatedSearchBox
