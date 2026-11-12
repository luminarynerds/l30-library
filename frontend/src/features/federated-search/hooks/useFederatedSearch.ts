/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * useFederatedSearch Hook
 *
 * Main hook for executing federated searches with React Query integration.
 * Handles search state management, result caching, and source-specific status tracking.
 */

import { useCallback, useState, useRef, useEffect } from 'react'
import { useQuery, UseQueryResult } from '@tanstack/react-query'
import * as api from '../services/federatedSearchApi'
import type {
  FederatedSearchQuery,
  FederatedSearchResponse,
  FederatedSearchState,
  FederatedSearchError,
  SearchSource,
  FederatedSearchResult,
  ResultAttribution,
} from '../types/federated-search.types'

// ==================== Types ====================

interface UseFederatedSearchOptions {
  /** Enable automatic execution when query changes */
  enabled?: boolean
  /** Cache time in milliseconds */
  cacheTime?: number
  /** Stale time in milliseconds */
  staleTime?: number
  /** Called when search completes */
  onSuccess?: (data: FederatedSearchResponse) => void
  /** Called when search fails */
  onError?: (error: FederatedSearchError) => void
  /** Called when search starts */
  onStart?: () => void
}

interface UseFederatedSearchResult {
  /** Search state */
  state: FederatedSearchState
  /** React Query result object */
  query: UseQueryResult<FederatedSearchResponse, FederatedSearchError>
  /** Execute search manually */
  search: (query: FederatedSearchQuery) => Promise<FederatedSearchResponse>
  /** Cancel current search */
  cancel: () => void
  /** Clear search results */
  clear: () => void
  /** Update search filters */
  updateFilters: (filters: FederatedSearchQuery['filters']) => void
  /** Change current page */
  setPage: (page: number) => void
  /** Is search loading */
  isLoading: boolean
  /** Is search error */
  isError: boolean
  /** Current error */
  error: FederatedSearchError | null
}

// ==================== Hook Implementation ====================

export function useFederatedSearch(options: UseFederatedSearchOptions = {}): UseFederatedSearchResult {
  const {
    enabled = true,
    cacheTime = 1000 * 60 * 5, // 5 minutes
    staleTime = 1000 * 60, // 1 minute
    onSuccess,
    onError,
    onStart,
  } = options

  // State management
  const [currentQuery, setCurrentQuery] = useState<FederatedSearchQuery | null>(null)
  const [state, setState] = useState<FederatedSearchState>({
    query: '',
    status: 'idle',
    page: 1,
    results: [],
    total: 0,
    sourceStatus: [],
  })

  const abortControllerRef = useRef<AbortController | null>(null)

  // Create query key for caching
  const queryKey = currentQuery
    ? (['federatedSearch', currentQuery.q, currentQuery.sources, currentQuery.filters, currentQuery.page] as const)
    : (['federatedSearch'] as const)

  // React Query hook for fetching
  const queryResult = useQuery<FederatedSearchResponse, FederatedSearchError>({
    queryKey,
    queryFn: async () => {
      if (!currentQuery) throw new Error('No query specified')

      setState(prev => ({
        ...prev,
        status: 'searching',
        sourceStatus: [],
      }))

      onStart?.()

      try {
        const response = await api.executeFederatedSearch(currentQuery)

        setState(prev => ({
          ...prev,
          query: response.query,
          status: 'success',
          results: response.results,
          total: response.total,
          page: response.page,
          sourceStatus: response.queriedSources.map((source: SearchSource) => ({
            source,
            status: 'success' as const,
            resultCount: response.results.filter((r: FederatedSearchResult) =>
              r.attribution.some((attr: ResultAttribution) => attr.source === source)
            ).length,
            timeMs: response.executionTimeMs,
          })),
          searchedAt: response.searchedAt,
          timeMs: response.executionTimeMs,
        }))

        onSuccess?.(response)
        return response
      } catch (error: unknown) {
        const federatedError = error as FederatedSearchError

        setState(prev => ({
          ...prev,
          status: 'error',
          error: federatedError.message,
        }))

        onError?.(federatedError)
        throw federatedError
      }
    },
    enabled: enabled && currentQuery !== null,
    gcTime: cacheTime,
    staleTime,
    retry: 1,
  })

  /**
   * Execute a search
   *
   * @param query - Search query parameters
   * @returns Promise resolving to search results
   */
  const search = useCallback(
    async (query: FederatedSearchQuery): Promise<FederatedSearchResponse> => {
      // Reset pagination when new query is made
      const fullQuery: FederatedSearchQuery = {
        ...query,
        page: query.page ?? 1,
      }

      setCurrentQuery(fullQuery)
      // Query will be executed automatically via React Query
      return new Promise<FederatedSearchResponse>((resolve, reject) => {
        // Wait for query to complete
        const checkQuery = setInterval(() => {
          if (queryResult.status === 'success' && queryResult.data) {
            clearInterval(checkQuery)
            resolve(queryResult.data as FederatedSearchResponse)
          } else if (queryResult.status === 'error') {
            clearInterval(checkQuery)
            reject(queryResult.error)
          }
        }, 100)

        setTimeout(() => {
          clearInterval(checkQuery)
          reject(new Error('Search timed out'))
        }, (query.timeout ?? 30000) + 1000)
      })
    },
    [queryResult]
  )

  /**
   * Cancel current search
   */
  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    api.cancelCurrentSearch()
    setState(prev => ({
      ...prev,
      status: 'cancelled',
    }))
  }, [])

  /**
   * Clear search results
   */
  const clear = useCallback(() => {
    setCurrentQuery(null)
    setState({
      query: '',
      status: 'idle',
      page: 1,
      results: [],
      total: 0,
      sourceStatus: [],
    })
  }, [])

  /**
   * Update search filters and re-execute
   *
   * @param filters - New filters
   */
  const updateFilters = useCallback(
    (filters: FederatedSearchQuery['filters']) => {
      if (!currentQuery) return

      const updatedQuery: FederatedSearchQuery = {
        ...currentQuery,
        ...(filters !== undefined && { filters }),
        page: 1, // Reset to first page when filters change
      }

      setCurrentQuery(updatedQuery)
    },
    [currentQuery]
  )

  /**
   * Change current page and re-execute
   *
   * @param page - New page number
   */
  const setPage = useCallback(
    (page: number) => {
      if (!currentQuery) return

      const updatedQuery: FederatedSearchQuery = {
        ...currentQuery,
        page,
      }

      setCurrentQuery(updatedQuery)
    },
    [currentQuery]
  )

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        // eslint-disable-next-line react-hooks/exhaustive-deps
        abortControllerRef.current.abort()
      }
    }
  }, [])

  return {
    state,
    query: queryResult as UseQueryResult<FederatedSearchResponse, FederatedSearchError>,
    search,
    cancel,
    clear,
    updateFilters,
    setPage,
    isLoading: queryResult.isPending,
    isError: queryResult.isError,
    error: queryResult.error ?? null,
  }
}

export default useFederatedSearch
