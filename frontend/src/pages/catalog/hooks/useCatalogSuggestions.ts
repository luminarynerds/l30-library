/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState } from 'react'
import { getSearchSuggestions, type SearchSuggestion } from '@/api/pg-search-api'

interface Params {
  searchQuery: string
  activeQuery: string
  totalResults: number | undefined
}

export function useCatalogSuggestions({ searchQuery, activeQuery, totalResults }: Params) {
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1)
  const [didYouMean, setDidYouMean] = useState<string | null>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  // Fetch autocomplete suggestions as user types
  useEffect(() => {
    if (searchQuery.trim().length < 2) {
      setSuggestions([])
      return
    }

    const abortController = new AbortController()
    const timer = window.setTimeout(async () => {
      try {
        const response = await getSearchSuggestions(searchQuery.trim(), 6)
        if (!abortController.signal.aborted) {
          setSuggestions(response.suggestions || [])
        }
      } catch {
        if (!abortController.signal.aborted) {
          setSuggestions([])
        }
      }
    }, 200)

    return () => {
      window.clearTimeout(timer)
      abortController.abort()
    }
  }, [searchQuery])

  // Click outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Fetch "did you mean" when results are empty
  useEffect(() => {
    if (totalResults === 0 && activeQuery && activeQuery.trim().length >= 2) {
      let cancelled = false
      getSearchSuggestions(activeQuery.trim(), 1)
        .then(response => {
          if (cancelled) return
          if (response.suggestions && response.suggestions.length > 0) {
            const suggestion = response.suggestions[0]!
            const sugTitle = suggestion.title
            if (sugTitle && sugTitle.toLowerCase() !== activeQuery.toLowerCase()) {
              setDidYouMean(sugTitle)
            } else {
              setDidYouMean(null)
            }
          } else {
            setDidYouMean(null)
          }
        })
        .catch(() => { if (!cancelled) setDidYouMean(null) })
      return () => { cancelled = true }
    } else {
      setDidYouMean(null)
    }
  }, [totalResults, activeQuery])

  const resetSuggestions = () => {
    setShowSuggestions(false)
    setSuggestions([])
    setSelectedSuggestionIndex(-1)
  }

  return {
    suggestions,
    showSuggestions,
    setShowSuggestions,
    selectedSuggestionIndex,
    setSelectedSuggestionIndex,
    didYouMean,
    setDidYouMean,
    suggestionsRef,
    resetSuggestions,
  }
}
