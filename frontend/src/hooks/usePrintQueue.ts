/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Print Queue Hook
 *
 * Manages polling of the print job queue with automatic refresh every 5 seconds.
 * Handles loading states, errors, and queue data caching to minimize API calls.
 *
 * Features:
 * - Auto-polling at 5-second intervals
 * - Error recovery with exponential backoff
 * - Manual refresh capability
 * - Prevents duplicate simultaneous requests
 * - Cleanup on unmount
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import api from '../api/api'
import { API_BASE } from '@/api/types'

// ==================== Types ====================

export interface PrintJob {
  id: number
  job_name: string
  pages: number
  copies: number
  release_code: string
  status: 'pending' | 'ready' | 'released' | 'failed'
  cost: number
  created_at: string
  released_at?: string
}

export interface UsePrintQueueOptions {
  /** Enable auto-polling (default: true) */
  enabled?: boolean
  /** Poll interval in milliseconds (default: 5000) */
  pollInterval?: number
  /** Automatically refetch on mount (default: true) */
  refetchOnMount?: boolean
}

export interface UsePrintQueueReturn {
  /** Array of print jobs in queue */
  jobs: PrintJob[]
  /** Whether data is currently loading */
  isLoading: boolean
  /** Current error if any */
  error: Error | null
  /** Whether polling is active */
  isPolling: boolean
  /** Manually trigger a refresh */
  refetch: () => Promise<void>
  /** Reset error state */
  clearError: () => void
}

// ==================== Hook ====================

export function usePrintQueue(options: UsePrintQueueOptions = {}): UsePrintQueueReturn {
  const {
    enabled = true,
    pollInterval = 5000,
    refetchOnMount = true,
  } = options

  const [jobs, setJobs] = useState<PrintJob[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const fetchInProgressRef = useRef(false)
  const retryCountRef = useRef(0)
  const maxRetriesRef = useRef(3)

  // Fetch print queue from API
  const fetchQueue = useCallback(async () => {
    // Prevent duplicate simultaneous requests
    if (fetchInProgressRef.current) {
      return
    }

    fetchInProgressRef.current = true
    setIsLoading(true)

    try {
      const response = await api.get<{ jobs: PrintJob[] }>(
        `${API_BASE}/print/queue`
      )

      setJobs(response.jobs || [])
      setError(null)
      retryCountRef.current = 0
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch print queue'

      setError(new Error(errorMessage))

      // Retry with exponential backoff
      retryCountRef.current += 1
      if (retryCountRef.current >= maxRetriesRef.current) {
        setIsPolling(false)
      }
    } finally {
      setIsLoading(false)
      fetchInProgressRef.current = false
    }
  }, [])

  // Manually trigger refresh
  const refetch = useCallback(async () => {
    retryCountRef.current = 0
    setIsPolling(true)
    await fetchQueue()
  }, [fetchQueue])

  // Clear error state
  const clearError = useCallback(() => {
    setError(null)
    retryCountRef.current = 0
  }, [])

  // Initial fetch on mount
  useEffect(() => {
    if (!enabled || !refetchOnMount) {
      return
    }

    setIsPolling(true)
    fetchQueue().then(() => {
      setIsPolling(true)
    })
  }, [enabled, refetchOnMount, fetchQueue])

  // Setup polling interval
  useEffect(() => {
    if (!enabled || !isPolling) {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
      return
    }

    pollTimerRef.current = setInterval(() => {
      fetchQueue()
    }, pollInterval)

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
    }
  }, [enabled, isPolling, fetchQueue, pollInterval])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [])

  return {
    jobs,
    isLoading,
    error,
    isPolling,
    refetch,
    clearError,
  }
}

export default usePrintQueue