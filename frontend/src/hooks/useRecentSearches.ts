/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * useRecentSearches Hook
 *
 * Manages recent search queries with localStorage persistence.
 * Features:
 * - Tracks last 10 search queries
 * - Prevents duplicate entries
 * - Cross-tab synchronization via storage events
 * - Timestamps for sorting by recency
 */

import { useState, useEffect, useCallback, useMemo } from 'react'

// ==================== Types ====================

export interface RecentSearch {
  query: string
  searchedAt: number // timestamp
  resultCount?: number // optional: how many results were found
}

export interface UseRecentSearchesReturn {
  recentSearches: RecentSearch[]
  addRecentSearch: (query: string, resultCount?: number) => void
  removeRecentSearch: (query: string) => void
  clearHistory: () => void
  getFilteredSearches: (prefix: string) => RecentSearch[]
}

// ==================== Constants ====================

const STORAGE_KEY = 'lsc-recent-searches'
const MAX_RECENT = 10

// ==================== Helpers ====================

function isStorageAvailable(): boolean {
  try {
    const test = '__storage_test__'
    localStorage.setItem(test, test)
    localStorage.removeItem(test)
    return true
  } catch {
    return false
  }
}

function loadFromStorage(): RecentSearch[] {
  if (!isStorageAvailable()) return []

  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return []
    return JSON.parse(stored) as RecentSearch[]
  } catch {
    return []
  }
}

function saveToStorage(searches: RecentSearch[]): void {
  if (!isStorageAvailable()) return

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(searches))
  } catch {
    // Handle quota exceeded silently
  }
}

// ==================== Hook ====================

export function useRecentSearches(): UseRecentSearchesReturn {
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>(() =>
    loadFromStorage()
  )

  // Sync with localStorage changes from other tabs
  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY && event.newValue) {
        try {
          const newSearches = JSON.parse(event.newValue) as RecentSearch[]
          setRecentSearches(newSearches)
        } catch {
          // Ignore parse errors
        }
      }
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [])

  // Add a search query to recent list
  const addRecentSearch = useCallback((query: string, resultCount?: number) => {
    const trimmedQuery = query.trim().toLowerCase()
    if (!trimmedQuery || trimmedQuery.length < 2) return

    setRecentSearches((prev: RecentSearch[]) => {
      // Remove existing entry if present (case-insensitive)
      const filtered = prev.filter(
        (s: RecentSearch) => s.query.toLowerCase() !== trimmedQuery
      )

      // Create new entry with original casing
      const newEntry: RecentSearch = {
        query: query.trim(),
        searchedAt: Date.now(),
        ...(resultCount !== undefined && { resultCount }),
      }

      // Add to front and limit to MAX_RECENT
      const updated = [newEntry, ...filtered].slice(0, MAX_RECENT)
      saveToStorage(updated)

      return updated
    })
  }, [])

  // Remove a search from history
  const removeRecentSearch = useCallback((query: string) => {
    setRecentSearches((prev: RecentSearch[]) => {
      const updated = prev.filter(
        (s: RecentSearch) => s.query.toLowerCase() !== query.toLowerCase()
      )
      saveToStorage(updated)
      return updated
    })
  }, [])

  // Clear all search history
  const clearHistory = useCallback(() => {
    setRecentSearches([])
    saveToStorage([])
  }, [])

  // Get searches that start with a given prefix
  const getFilteredSearches = useCallback(
    (prefix: string): RecentSearch[] => {
      if (!prefix.trim()) return recentSearches
      const lowerPrefix = prefix.toLowerCase()
      return recentSearches.filter((s: RecentSearch) =>
        s.query.toLowerCase().startsWith(lowerPrefix)
      )
    },
    [recentSearches]
  )

  // Sort by most recent
  const sortedSearches = useMemo(
    () => [...recentSearches].sort((a, b) => b.searchedAt - a.searchedAt),
    [recentSearches]
  )

  return {
    recentSearches: sortedSearches,
    addRecentSearch,
    removeRecentSearch,
    clearHistory,
    getFilteredSearches,
  }
}

export default useRecentSearches
