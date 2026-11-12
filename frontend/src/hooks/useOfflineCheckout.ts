/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Offline Checkout Hook
 *
 * React hook that wraps the offlineCheckoutQueue for use in staff checkout components.
 * Provides reactive state and seamless online/offline checkout handling.
 *
 * When online: Sends checkout directly to server, falls back to queue on failure
 * When offline: Queues operation immediately, syncs when back online
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useOnlineStatus } from './useServiceWorker'
import {
  enqueueCheckout,
  enqueueCheckin,
  enqueueRenewal,
  syncAllPending,
  getPendingOperations,
  getQueueStats,
  purgeCompleted,
  generateOfflineReceipt,
  type OfflineOperation,
  type QueueStats,
  type SyncResult,
} from '../lib/offlineCheckoutQueue'
import {
  lookupPatron,
  lookupItem,
  incrementPatronCheckouts,
  markItemCheckedOut,
  markItemAvailable,
} from '../lib/offlinePatronCache'
import { getAccessToken } from '../utils/tokenStore'

// ==================== Types ====================

export interface UseOfflineCheckoutReturn {
  /** Whether the app is online */
  isOnline: boolean
  /** Current queue statistics */
  queueStats: QueueStats
  /** Pending operations list */
  pendingOperations: OfflineOperation[]
  /** Whether a sync is in progress */
  isSyncing: boolean
  /** Last sync results */
  lastSyncResults: SyncResult[] | null
  /** Process a checkout (online or offline) */
  checkout: (patronBarcode: string, itemBarcode: string) => Promise<OfflineOperation>
  /** Process a checkin (online or offline) */
  checkin: (itemBarcode: string) => Promise<OfflineOperation>
  /** Process a renewal (online or offline) */
  renew: (patronBarcode: string, itemBarcode: string) => Promise<OfflineOperation>
  /** Manually trigger sync */
  syncNow: (token: string) => Promise<SyncResult[]>
  /** Generate receipt for offline operations */
  getReceipt: (patronName: string) => string
  /** Clean up old completed operations */
  cleanup: () => Promise<number>
  /** Look up a patron from the local cache */
  lookupPatron: (barcode: string) => Promise<import('../lib/offlinePatronCache').CachedPatron | null>
  /** Look up an item from the local cache */
  lookupItem: (barcode: string) => Promise<import('../lib/offlinePatronCache').CachedItem | null>
}

// ==================== Hook ====================

export function useOfflineCheckout(staffId: string): UseOfflineCheckoutReturn {
  const isOnline = useOnlineStatus()
  const queryClient = useQueryClient()

  const [queueStats, setQueueStats] = useState<QueueStats>({
    total: 0, pending: 0, syncing: 0, synced: 0, failed: 0, conflict: 0,
  })
  const [pendingOperations, setPendingOperations] = useState<OfflineOperation[]>([])
  const [isSyncing, setIsSyncing] = useState(false)
  const [lastSyncResults, setLastSyncResults] = useState<SyncResult[] | null>(null)

  const syncInProgressRef = useRef(false)

  // Refresh queue state from IndexedDB
  const refreshQueueState = useCallback(async () => {
    const [stats, pending] = await Promise.all([
      getQueueStats(),
      getPendingOperations(),
    ])
    setQueueStats(stats)
    setPendingOperations(pending)
  }, [])

  // Enqueue and refresh
  const checkout = useCallback(async (patronBarcode: string, itemBarcode: string) => {
    const op = await enqueueCheckout(patronBarcode, itemBarcode, staffId)
    await incrementPatronCheckouts(patronBarcode)
    await markItemCheckedOut(itemBarcode)
    await refreshQueueState()
    return op
  }, [staffId, refreshQueueState])

  const checkin = useCallback(async (itemBarcode: string) => {
    const op = await enqueueCheckin(itemBarcode, staffId)
    await markItemAvailable(itemBarcode)
    await refreshQueueState()
    return op
  }, [staffId, refreshQueueState])

  const renew = useCallback(async (patronBarcode: string, itemBarcode: string) => {
    const op = await enqueueRenewal(patronBarcode, itemBarcode, staffId)
    await refreshQueueState()
    return op
  }, [staffId, refreshQueueState])

  // Sync all pending operations
  const syncNow = useCallback(async (token: string): Promise<SyncResult[]> => {
    if (syncInProgressRef.current) return []
    syncInProgressRef.current = true
    setIsSyncing(true)

    try {
      const results = await syncAllPending(token)
      setLastSyncResults(results)
      await refreshQueueState()

      // Invalidate React Query caches for circulation data
      queryClient.invalidateQueries({ queryKey: ['circulation'] })
      queryClient.invalidateQueries({ queryKey: ['staff', 'circulation'] })
      queryClient.invalidateQueries({ queryKey: ['checkouts'] })

      return results
    } finally {
      syncInProgressRef.current = false
      setIsSyncing(false)
    }
  }, [refreshQueueState, queryClient])

  // Generate receipt from current pending operations
  const getReceipt = useCallback((patronName: string): string => {
    return generateOfflineReceipt(pendingOperations, patronName)
  }, [pendingOperations])

  // Cleanup old synced operations
  const cleanup = useCallback(async (): Promise<number> => {
    const count = await purgeCompleted()
    await refreshQueueState()
    return count
  }, [refreshQueueState])

  // Load initial queue state
  useEffect(() => {
    refreshQueueState()
  }, [refreshQueueState])

  // Auto-sync when coming back online. Token comes from the in-memory store
  // (the only real token source; the old 'lsc_auth_token' localStorage read
  // was always null, so auto-sync never actually fired). If the token isn't
  // in memory yet (e.g. right after a reload, before the cookie refresh
  // completes), the periodic queueStats refresh retriggers this effect.
  useEffect(() => {
    if (isOnline && queueStats.pending > 0 && !syncInProgressRef.current) {
      const token = getAccessToken()
      if (token) {
        syncNow(token)
      }
    }
  }, [isOnline, queueStats.pending, syncNow])

  // Periodic queue refresh
  useEffect(() => {
    const interval = setInterval(refreshQueueState, 10000) // Every 10s
    return () => clearInterval(interval)
  }, [refreshQueueState])

  return {
    isOnline,
    queueStats,
    pendingOperations,
    isSyncing,
    lastSyncResults,
    checkout,
    checkin,
    renew,
    syncNow,
    getReceipt,
    cleanup,
    lookupPatron,
    lookupItem,
  }
}

export default useOfflineCheckout
