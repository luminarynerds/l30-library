/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * useInventoryScanner - Core hook for mobile inventory scanning.
 *
 * Handles: scanning items while walking shelves, offline queue with sync,
 * out-of-order detection, missing item tracking, pause/resume,
 * completion percentage, time estimation, and gamification messages.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import type { SectionItem, BatchScanInput } from '@/api/mobile-scanning-api'
import { batchScanItems } from '@/api/mobile-scanning-api'

const STORAGE_KEY_PREFIX = 'lsc_inventory_scan_'

// ==================== Types ====================

export type ScanStatus = 'found' | 'not_on_shelf' | 'out_of_order' | 'already_scanned'

export interface ScanRecord {
  barcode: string
  timestamp: string
  status: ScanStatus
  title?: string | null
  expectedIndex?: number
  actualIndex?: number
  synced: boolean
}

export interface ScanSessionState {
  auditId: number
  section: string
  expectedItems: SectionItem[]
  scannedBarcodes: Set<string>
  scanRecords: ScanRecord[]
  startedAt: string
  pausedAt: string | null
  totalPausedMs: number
  isActive: boolean
}

export interface ScannerStats {
  totalExpected: number
  totalScanned: number
  totalMissing: number
  totalOutOfOrder: number
  totalNotOnShelf: number
  completionPct: number
  estimatedRemainingMs: number | null
  scanRate: number // items per minute
  elapsedMs: number
}

interface PersistedSession {
  auditId: number
  section: string
  expectedItems: SectionItem[]
  scannedBarcodes: string[]
  scanRecords: ScanRecord[]
  startedAt: string
  pausedAt: string | null
  totalPausedMs: number
  isActive: boolean
}

// ==================== Gamification Messages ====================

const ENCOURAGEMENT_MESSAGES = [
  (pct: number, section: string) => `You're ${pct}% done with ${section}!`,
  (pct: number) => `${pct}% complete — keep scanning!`,
  (_: number, section: string) => `Great pace on ${section}!`,
  (pct: number) => `${pct}% there — you've got this!`,
  () => 'Steady scanning rhythm!',
]

const MILESTONE_MESSAGES: Record<number, string> = {
  25: 'Quarter done! The shelves are looking organized.',
  50: 'Halfway there! You\'re making great progress.',
  75: 'Almost done — the finish line is in sight!',
  90: 'So close! Just a few more items to go.',
  100: 'Section complete! Inventory champion!',
}

function getEncouragement(pct: number, section: string): string | null {
  const milestone = Object.keys(MILESTONE_MESSAGES)
    .map(Number)
    .find((m) => pct >= m && pct < m + 2)

  if (milestone !== undefined) {
    const msg = MILESTONE_MESSAGES[milestone]
    if (msg) return msg
  }

  // Periodic encouragement every ~10%
  if (pct > 0 && pct % 10 < 2) {
    const idx = Math.floor(pct / 10) % ENCOURAGEMENT_MESSAGES.length
    const fn = ENCOURAGEMENT_MESSAGES[idx]
    if (fn) return fn(Math.round(pct), section)
  }

  return null
}

// ==================== Persistence Helpers ====================

function getStorageKey(auditId: number, section: string): string {
  return `${STORAGE_KEY_PREFIX}${auditId}_${section.replace(/\+/g, '_')}`
}

function saveSession(session: ScanSessionState): void {
  try {
    const key = getStorageKey(session.auditId, session.section)
    const persisted: PersistedSession = {
      ...session,
      scannedBarcodes: Array.from(session.scannedBarcodes),
    }
    localStorage.setItem(key, JSON.stringify(persisted))
  } catch { /* storage full */ }
}

function loadSession(auditId: number, section: string): ScanSessionState | null {
  try {
    const key = getStorageKey(auditId, section)
    const stored = localStorage.getItem(key)
    if (!stored) return null
    const persisted: PersistedSession = JSON.parse(stored)
    return {
      ...persisted,
      scannedBarcodes: new Set(persisted.scannedBarcodes),
    }
  } catch {
    return null
  }
}

function clearSessionStorage(auditId: number, section: string): void {
  try {
    localStorage.removeItem(getStorageKey(auditId, section))
  } catch { /* ignore */ }
}

// ==================== Offline Queue ====================

const OFFLINE_QUEUE_KEY = 'lsc_inventory_offline_queue'

interface OfflineQueueItem {
  auditId: number
  scan: BatchScanInput
  timestamp: string
}

function getOfflineQueue(): OfflineQueueItem[] {
  try {
    const stored = localStorage.getItem(OFFLINE_QUEUE_KEY)
    return stored ? JSON.parse(stored) : []
  } catch { return [] }
}

function addToOfflineQueue(item: OfflineQueueItem): void {
  try {
    const queue = getOfflineQueue()
    queue.push(item)
    localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue))
  } catch { /* full */ }
}

function clearOfflineQueue(): void {
  try { localStorage.removeItem(OFFLINE_QUEUE_KEY) } catch { /* ignore */ }
}

// ==================== Hook ====================

export function useInventoryScanner(
  auditId: number | null,
  section: string,
  expectedItems: SectionItem[],
) {
  const [session, setSession] = useState<ScanSessionState | null>(null)
  const [lastScanResult, setLastScanResult] = useState<ScanRecord | null>(null)
  const [encouragement, setEncouragement] = useState<string | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const lastScanIndex = useRef(0)
  const syncTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const syncFnRef = useRef<() => void>(() => {})

  // Build a lookup from barcode to expected index
  const barcodeIndexMap = useMemo(() => {
    const map = new Map<string, number>()
    expectedItems.forEach((item, idx) => map.set(item.barcode, idx))
    return map
  }, [expectedItems])

  // Online/offline tracking
  useEffect(() => {
    const onOnline = () => setIsOnline(true)
    const onOffline = () => setIsOnline(false)
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    return () => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
    }
  }, [])

  // Restore session from localStorage on mount
  useEffect(() => {
    if (!auditId || !section) return
    const restored = loadSession(auditId, section)
    if (restored && restored.isActive) {
      setSession(restored)
      // Restore lastScanIndex
      const maxIdx = restored.scanRecords.reduce((max, r) => {
        const idx = barcodeIndexMap.get(r.barcode)
        return idx !== undefined && idx > max ? idx : max
      }, 0)
      lastScanIndex.current = maxIdx
    }
  }, [auditId, section, barcodeIndexMap])

  // Persist session on every change
  useEffect(() => {
    if (session) saveSession(session)
  }, [session])

  // Start a new scanning session
  const startSession = useCallback(() => {
    if (!auditId) return
    const newSession: ScanSessionState = {
      auditId,
      section,
      expectedItems,
      scannedBarcodes: new Set(),
      scanRecords: [],
      startedAt: new Date().toISOString(),
      pausedAt: null,
      totalPausedMs: 0,
      isActive: true,
    }
    lastScanIndex.current = 0
    setSession(newSession)
    setLastScanResult(null)
    setEncouragement(null)
  }, [auditId, section, expectedItems])

  // Resume a paused session
  const resumeSession = useCallback(() => {
    setSession((prev) => {
      if (!prev || !prev.pausedAt) return prev
      const pausedDuration = Date.now() - new Date(prev.pausedAt).getTime()
      return {
        ...prev,
        pausedAt: null,
        totalPausedMs: prev.totalPausedMs + pausedDuration,
        isActive: true,
      }
    })
  }, [])

  // Pause the session
  const pauseSession = useCallback(() => {
    setSession((prev) => {
      if (!prev || prev.pausedAt) return prev
      return {
        ...prev,
        pausedAt: new Date().toISOString(),
        isActive: false,
      }
    })
  }, [])

  // Scan a barcode
  const scanBarcode = useCallback((barcode: string) => {
    if (!session || !session.isActive || session.pausedAt) return null

    // Already scanned?
    if (session.scannedBarcodes.has(barcode)) {
      const record: ScanRecord = {
        barcode,
        timestamp: new Date().toISOString(),
        status: 'already_scanned',
        synced: true,
      }
      setLastScanResult(record)
      return record
    }

    const expectedIndex = barcodeIndexMap.get(barcode)
    let scanStatus: ScanStatus
    let title: string | null = null

    if (expectedIndex === undefined) {
      // Not in expected items for this section
      scanStatus = 'not_on_shelf'
    } else {
      title = expectedItems[expectedIndex]?.catalog_title ?? null
      // Check order
      if (expectedIndex < lastScanIndex.current) {
        scanStatus = 'out_of_order'
      } else {
        scanStatus = 'found'
        lastScanIndex.current = expectedIndex
      }
    }

    const record: ScanRecord = {
      barcode,
      timestamp: new Date().toISOString(),
      status: scanStatus,
      title,
      ...(expectedIndex !== undefined ? { expectedIndex } : {}),
      actualIndex: session.scanRecords.length,
      synced: false,
    }

    const updatedBarcodes = new Set(session.scannedBarcodes)
    updatedBarcodes.add(barcode)

    const updatedRecords = [...session.scanRecords, record]
    setSession({
      ...session,
      scannedBarcodes: updatedBarcodes,
      scanRecords: updatedRecords,
    })
    setLastScanResult(record)

    // Queue for sync
    if (auditId) {
      addToOfflineQueue({
        auditId,
        scan: { barcode, found_at_location: section },
        timestamp: record.timestamp,
      })
    }

    // Gamification
    const pct = (updatedBarcodes.size / Math.max(expectedItems.length, 1)) * 100
    const msg = getEncouragement(pct, section)
    if (msg) setEncouragement(msg)

    // Auto-sync debounce
    if (syncTimeoutRef.current) clearTimeout(syncTimeoutRef.current)
    syncTimeoutRef.current = setTimeout(() => {
      if (navigator.onLine) syncFnRef.current()
    }, 3000)

    return record
  }, [session, barcodeIndexMap, expectedItems, section, auditId])

  // Sync offline queue to server
  const syncOfflineQueue = useCallback(async () => {
    if (!auditId || isSyncing) return
    const queue = getOfflineQueue()
    if (queue.length === 0) return

    setIsSyncing(true)
    try {
      // Group by audit
      const auditScans = queue
        .filter((q) => q.auditId === auditId)
        .map((q) => q.scan)

      if (auditScans.length > 0) {
        await batchScanItems(auditId, auditScans)
      }

      // Mark synced
      setSession((prev) => {
        if (!prev) return prev
        const syncedBarcodes = new Set(auditScans.map((s) => s.barcode))
        return {
          ...prev,
          scanRecords: prev.scanRecords.map((r) =>
            syncedBarcodes.has(r.barcode) ? { ...r, synced: true } : r,
          ),
        }
      })

      clearOfflineQueue()
    } catch {
      // Will retry later
    } finally {
      setIsSyncing(false)
    }
  }, [auditId, isSyncing])

  // Keep ref in sync
  useEffect(() => { syncFnRef.current = syncOfflineQueue }, [syncOfflineQueue])

  // Sync when coming back online
  useEffect(() => {
    if (isOnline && session?.isActive) {
      syncOfflineQueue()
    }
  }, [isOnline, session?.isActive, syncOfflineQueue])

  // Complete the session
  const completeSession = useCallback(async () => {
    // Final sync
    await syncOfflineQueue()
    setSession((prev) => {
      if (!prev) return prev
      const completed = { ...prev, isActive: false }
      clearSessionStorage(prev.auditId, prev.section)
      return completed
    })
    setEncouragement('Section complete! Inventory champion!')
  }, [syncOfflineQueue])

  // Compute stats
  const stats: ScannerStats = useMemo(() => {
    if (!session) {
      return {
        totalExpected: expectedItems.length,
        totalScanned: 0,
        totalMissing: expectedItems.length,
        totalOutOfOrder: 0,
        totalNotOnShelf: 0,
        completionPct: 0,
        estimatedRemainingMs: null,
        scanRate: 0,
        elapsedMs: 0,
      }
    }

    const scannedCount = session.scannedBarcodes.size
    const outOfOrder = session.scanRecords.filter((r) => r.status === 'out_of_order').length
    const notOnShelf = session.scanRecords.filter((r) => r.status === 'not_on_shelf').length
    const total = expectedItems.length
    const completionPct = total > 0 ? (scannedCount / total) * 100 : 0

    // Time calculation
    const started = new Date(session.startedAt).getTime()
    const now = session.pausedAt ? new Date(session.pausedAt).getTime() : Date.now()
    const elapsedMs = now - started - session.totalPausedMs
    const scanRate = elapsedMs > 0 ? (scannedCount / elapsedMs) * 60000 : 0 // per minute
    const remaining = total - scannedCount
    const estimatedRemainingMs = scanRate > 0 ? (remaining / scanRate) * 60000 : null

    // Missing items = expected items that haven't been scanned
    const missingCount = total - scannedCount

    return {
      totalExpected: total,
      totalScanned: scannedCount,
      totalMissing: Math.max(0, missingCount),
      totalOutOfOrder: outOfOrder,
      totalNotOnShelf: notOnShelf,
      completionPct: Math.min(100, Math.round(completionPct * 10) / 10),
      estimatedRemainingMs,
      scanRate: Math.round(scanRate * 10) / 10,
      elapsedMs,
    }
  }, [session, expectedItems.length])

  // Get items that haven't been scanned yet (potentially missing)
  const missingItems = useMemo(() => {
    if (!session) return expectedItems
    return expectedItems.filter((item) => !session.scannedBarcodes.has(item.barcode))
  }, [session, expectedItems])

  // Get out-of-order scan records
  const outOfOrderScans = useMemo(() => {
    if (!session) return []
    return session.scanRecords.filter((r) => r.status === 'out_of_order')
  }, [session])

  // Get not-on-shelf scan records
  const notOnShelfScans = useMemo(() => {
    if (!session) return []
    return session.scanRecords.filter((r) => r.status === 'not_on_shelf')
  }, [session])

  // Pending offline count
  const pendingOfflineCount = useMemo(() => {
    if (!session) return 0
    return session.scanRecords.filter((r) => !r.synced).length
  }, [session])

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (syncTimeoutRef.current) clearTimeout(syncTimeoutRef.current)
    }
  }, [])

  return {
    // Session management
    session,
    startSession,
    pauseSession,
    resumeSession,
    completeSession,
    isSessionActive: session?.isActive && !session?.pausedAt,
    isPaused: !!session?.pausedAt,

    // Scanning
    scanBarcode,
    lastScanResult,

    // Stats & progress
    stats,
    missingItems,
    outOfOrderScans,
    notOnShelfScans,

    // Offline
    isOnline,
    isSyncing,
    pendingOfflineCount,
    syncOfflineQueue,

    // Gamification
    encouragement,
  }
}
