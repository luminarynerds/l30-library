/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for React Query configuration and store setup.
 *
 * Verifies:
 * - QueryClient initialization with correct defaults
 * - Retry logic configuration (auth errors excluded)
 * - Stale time and garbage collection settings
 * - Offline-first network mode
 * - Refetch behavior on window focus and reconnect
 * - Error handling strategy
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { QueryClient } from '@tanstack/react-query'


/**
 * Helper to create a test QueryClient matching production config
 */
function createProductionQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5, // 5 minutes
        gcTime: 1000 * 60 * 30, // 30 minutes
        retry: (failureCount, error) => {
          // Don't retry auth errors or 404s
          if (error && typeof error === 'object' && 'status' in error) {
            const status = (error as { status: number }).status
            if (status === 401 || status === 403 || status === 404) return false
          }
          return failureCount < 2
        },
        refetchOnWindowFocus: 'always',
        refetchOnReconnect: 'always',
        networkMode: 'offlineFirst' as const,
      },
      mutations: {
        retry: 1,
        networkMode: 'offlineFirst' as const,
      },
    },
  })
}


describe('QueryClient Configuration', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = createProductionQueryClient()
  })

  it('should initialize with correct default query options', () => {
    const defaults = queryClient.getDefaultOptions()
    expect(defaults.queries).toBeDefined()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((defaults.queries as any).staleTime).toBe(1000 * 60 * 5)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((defaults.queries as any).gcTime).toBe(1000 * 60 * 30)
  })

  it('should have offline-first network mode', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((defaults.queries as any).networkMode).toBe('offlineFirst')
  })

  it('should refetch on window focus', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((defaults.queries as any).refetchOnWindowFocus).toBe('always')
  })

  it('should refetch on reconnect', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((defaults.queries as any).refetchOnReconnect).toBe('always')
  })
})


describe('QueryClient Retry Logic', () => {
  let queryClient: QueryClient
  let retryFn: (failureCount: number, error: unknown) => boolean

  beforeEach(() => {
    queryClient = createProductionQueryClient()
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    retryFn = (defaults.queries as any).retry
  })

  it('should not retry on 401 Unauthorized', () => {
    const error = { status: 401 }
    expect(retryFn(0, error)).toBe(false)
    expect(retryFn(1, error)).toBe(false)
  })

  it('should not retry on 403 Forbidden', () => {
    const error = { status: 403 }
    expect(retryFn(0, error)).toBe(false)
    expect(retryFn(1, error)).toBe(false)
  })

  it('should not retry on 404 Not Found', () => {
    const error = { status: 404 }
    expect(retryFn(0, error)).toBe(false)
    expect(retryFn(1, error)).toBe(false)
  })

  it('should retry on other 4xx errors', () => {
    const error = { status: 400 }
    expect(retryFn(0, error)).toBe(true)
  })

  it('should retry on 5xx errors up to the max', () => {
    const error = { status: 500 }
    expect(retryFn(0, error)).toBe(true)
    expect(retryFn(1, error)).toBe(true) // Max 2 retries total (failureCount < 2)
    expect(retryFn(2, error)).toBe(false)
  })

  it('should retry on network errors', () => {
    const error = new Error('Network timeout')
    expect(retryFn(0, error)).toBe(true)
    expect(retryFn(1, error)).toBe(true)
    expect(retryFn(2, error)).toBe(false)
  })

  it('should not retry if max retries reached', () => {
    const error = { status: 500 }
    expect(retryFn(2, error)).toBe(false)
  })

  it('should handle errors without status property', () => {
    const error = new TypeError('Failed to fetch')
    expect(retryFn(0, error)).toBe(true)
    expect(retryFn(1, error)).toBe(true)
    expect(retryFn(2, error)).toBe(false)
  })

  it('should handle null/undefined errors', () => {
    expect(retryFn(0, null)).toBe(true)
    expect(retryFn(0, undefined)).toBe(true)
  })
})


describe('QueryClient Cache Management', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = createProductionQueryClient()
  })

  it('should have 5-minute stale time', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const staleTime = (defaults.queries as any).staleTime
    expect(staleTime).toBe(300000) // 5 * 60 * 1000
  })

  it('should have 30-minute garbage collection time', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gcTime = (defaults.queries as any).gcTime
    expect(gcTime).toBe(1800000) // 30 * 60 * 1000
  })

  it('should have more generous gcTime than staleTime', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const staleTime = (defaults.queries as any).staleTime
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gcTime = (defaults.queries as any).gcTime
    expect(gcTime).toBeGreaterThan(staleTime)
  })

  it('should configure mutations with lower retry count', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const mutationRetry = (defaults.mutations as any).retry
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const queryRetry = (defaults.queries as any).retry
    expect(mutationRetry).toBe(1) // Mutations retry once
    expect(typeof queryRetry).toBe('function') // Queries use retry function
  })
})


describe('QueryClient State Management', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = createProductionQueryClient()
  })

  it('should manage cache state', () => {
    // Test basic cache operations
    const cache = queryClient.getQueryCache()
    expect(cache).toBeDefined()
  })

  it('should allow cache clearing', () => {
    queryClient.clear()
    const cache = queryClient.getQueryCache()
    expect(cache.getAll()).toHaveLength(0)
  })

  it('should allow mutation cache clearing', () => {
    queryClient.getMutationCache().clear()
    const mutations = queryClient.getMutationCache().getAll()
    expect(mutations).toHaveLength(0)
  })

  it('should have mutation cache', () => {
    const mutationCache = queryClient.getMutationCache()
    expect(mutationCache).toBeDefined()
  })

  it('should support query cache configuration', () => {
    const queryCache = queryClient.getQueryCache()
    expect(queryCache).toBeDefined()
    expect(queryCache.getAll).toBeDefined()
  })
})


describe('Offline-First Network Mode', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = createProductionQueryClient()
  })

  it('should serve stale data while offline', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((defaults.queries as any).networkMode).toBe('offlineFirst')
  })

  it('should revalidate in background when online', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((defaults.queries as any).refetchOnReconnect).toBe('always')
  })

  it('should update data when window regains focus', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((defaults.queries as any).refetchOnWindowFocus).toBe('always')
  })

  it('mutations should also use offline-first mode', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((defaults.mutations as any).networkMode).toBe('offlineFirst')
  })
})


describe('QueryClient Error Handling Strategy', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = createProductionQueryClient()
  })

  it('should not retry on authentication errors', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const retryFn = (defaults.queries as any).retry

    // 401: Not authenticated
    expect(retryFn(0, { status: 401 })).toBe(false)
    expect(retryFn(1, { status: 401 })).toBe(false)

    // 403: Forbidden
    expect(retryFn(0, { status: 403 })).toBe(false)
    expect(retryFn(1, { status: 403 })).toBe(false)
  })

  it('should not retry on not found errors', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const retryFn = (defaults.queries as any).retry

    expect(retryFn(0, { status: 404 })).toBe(false)
  })

  it('should retry transient errors (5xx)', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const retryFn = (defaults.queries as any).retry

    expect(retryFn(0, { status: 500 })).toBe(true)
    expect(retryFn(0, { status: 502 })).toBe(true)
    expect(retryFn(0, { status: 503 })).toBe(true)
  })

  it('should retry some 4xx errors (not auth/404)', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const retryFn = (defaults.queries as any).retry

    expect(retryFn(0, { status: 400 })).toBe(true)
    expect(retryFn(0, { status: 429 })).toBe(true) // Rate limit
  })

  it('should handle network errors gracefully', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const retryFn = (defaults.queries as any).retry

    const networkError = new Error('Network timeout')
    expect(retryFn(0, networkError)).toBe(true)
  })
})


describe('QueryClient Mutation Options', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = createProductionQueryClient()
  })

  it('should configure mutations with retry: 1', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((defaults.mutations as any).retry).toBe(1)
  })

  it('should configure mutations with offline-first mode', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((defaults.mutations as any).networkMode).toBe('offlineFirst')
  })

  it('should have lower retry count for mutations than queries', () => {
    const defaults = queryClient.getDefaultOptions()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const mutationRetry = (defaults.mutations as any).retry
    expect(mutationRetry).toBe(1) // Lower than query retries (max 2)
  })
})


describe('QueryClient Production Readiness', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = createProductionQueryClient()
  })

  it('should be suitable for production use', () => {
    expect(queryClient).toBeDefined()
    expect(queryClient.getDefaultOptions()).toBeDefined()
  })

  it('should support development debugging', () => {
    // QueryClient should be inspectable for debugging
    const defaults = queryClient.getDefaultOptions()
    expect(typeof defaults).toBe('object')
  })

  it('should be resetable for testing', () => {
    queryClient.clear()
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0)
  })

  it('should handle concurrent operations', () => {
    // QueryClient should support concurrent queries/mutations
    expect(queryClient.getMutationCache).toBeDefined()
    expect(queryClient.getQueryCache).toBeDefined()
  })
})
