/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { API_BASE } from '@/api/types'
/**
 * Offline Checkout Queue
 *
 * IndexedDB-backed queue for staff checkout operations that can work offline.
 * When the network is unavailable, checkout/checkin operations are stored locally
 * and synced when connectivity is restored.
 *
 * Features:
 * - IndexedDB persistence (survives page reload)
 * - Ordered queue with timestamps
 * - Retry logic with exponential backoff
 * - Conflict detection on sync
 * - Receipt generation for offline checkouts
 * - Queue status reporting
 */

// ==================== Types ====================

export type OfflineOperationType = 'checkout' | 'checkin' | 'renew'

export interface OfflineOperation {
  /** Unique operation ID */
  id: string
  /** Operation type */
  type: OfflineOperationType
  /** Patron barcode or ID */
  patronIdentifier: string
  /** Item barcode */
  itemBarcode: string
  /** Staff user who initiated the operation */
  staffId: string
  /** When the operation was created */
  timestamp: string
  /** Number of sync attempts */
  retryCount: number
  /** Last sync attempt timestamp */
  lastAttempt: string | null
  /** Sync status */
  status: 'pending' | 'syncing' | 'synced' | 'failed' | 'conflict'
  /** Error message if failed */
  error: string | null
  /** Server response after sync */
  serverResponse: unknown | null
}

export interface QueueStats {
  total: number
  pending: number
  syncing: number
  synced: number
  failed: number
  conflict: number
}

export interface SyncResult {
  operation: OfflineOperation
  success: boolean
  error?: string
  conflict?: boolean
}

// ==================== Constants ====================

const DB_NAME = 'lsc-offline-checkout'
const DB_VERSION = 1
const STORE_NAME = 'operations'
const MAX_RETRIES = 5

// ==================== IndexedDB Helpers ====================

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result

      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' })
        store.createIndex('status', 'status', { unique: false })
        store.createIndex('timestamp', 'timestamp', { unique: false })
        store.createIndex('patronIdentifier', 'patronIdentifier', { unique: false })
      }
    }
  })
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

// ==================== Queue Operations ====================

export async function enqueueCheckout(
  patronIdentifier: string,
  itemBarcode: string,
  staffId: string,
): Promise<OfflineOperation> {
  return enqueueOperation('checkout', patronIdentifier, itemBarcode, staffId)
}

export async function enqueueCheckin(
  itemBarcode: string,
  staffId: string,
): Promise<OfflineOperation> {
  return enqueueOperation('checkin', '', itemBarcode, staffId)
}

export async function enqueueRenewal(
  patronIdentifier: string,
  itemBarcode: string,
  staffId: string,
): Promise<OfflineOperation> {
  return enqueueOperation('renew', patronIdentifier, itemBarcode, staffId)
}

async function enqueueOperation(
  type: OfflineOperationType,
  patronIdentifier: string,
  itemBarcode: string,
  staffId: string,
): Promise<OfflineOperation> {
  const operation: OfflineOperation = {
    id: generateId(),
    type,
    patronIdentifier,
    itemBarcode,
    staffId,
    timestamp: new Date().toISOString(),
    retryCount: 0,
    lastAttempt: null,
    status: 'pending',
    error: null,
    serverResponse: null,
  }

  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const request = store.add(operation)

    request.onsuccess = () => resolve(operation)
    request.onerror = () => reject(request.error)
    tx.oncomplete = () => db.close()
  })
}

export async function getPendingOperations(): Promise<OfflineOperation[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const index = store.index('status')
    const request = index.getAll('pending')

    request.onsuccess = () => {
      const ops = request.result as OfflineOperation[]
      ops.sort((a, b) => a.timestamp.localeCompare(b.timestamp))
      resolve(ops)
    }
    request.onerror = () => reject(request.error)
    tx.oncomplete = () => db.close()
  })
}

export async function getAllOperations(): Promise<OfflineOperation[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const request = store.getAll()

    request.onsuccess = () => {
      const ops = request.result as OfflineOperation[]
      ops.sort((a, b) => a.timestamp.localeCompare(b.timestamp))
      resolve(ops)
    }
    request.onerror = () => reject(request.error)
    tx.oncomplete = () => db.close()
  })
}

async function updateOperation(operation: OfflineOperation): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const request = store.put(operation)

    request.onsuccess = () => resolve()
    request.onerror = () => reject(request.error)
    tx.oncomplete = () => db.close()
  })
}

export async function purgeCompleted(maxAgeMs: number = 24 * 60 * 60 * 1000): Promise<number> {
  const db = await openDB()
  const cutoff = new Date(Date.now() - maxAgeMs).toISOString()

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const index = store.index('status')
    const request = index.openCursor('synced')
    let deleted = 0

    request.onsuccess = () => {
      const cursor = request.result
      if (cursor) {
        const op = cursor.value as OfflineOperation
        if (op.timestamp < cutoff) {
          cursor.delete()
          deleted++
        }
        cursor.continue()
      }
    }
    request.onerror = () => reject(request.error)
    tx.oncomplete = () => {
      db.close()
      resolve(deleted)
    }
  })
}

export async function getQueueStats(): Promise<QueueStats> {
  const operations = await getAllOperations()
  return {
    total: operations.length,
    pending: operations.filter(op => op.status === 'pending').length,
    syncing: operations.filter(op => op.status === 'syncing').length,
    synced: operations.filter(op => op.status === 'synced').length,
    failed: operations.filter(op => op.status === 'failed').length,
    conflict: operations.filter(op => op.status === 'conflict').length,
  }
}

// ==================== Sync Logic ====================

async function syncOperation(
  operation: OfflineOperation,
  token: string,
): Promise<SyncResult> {
  operation.status = 'syncing'
  operation.lastAttempt = new Date().toISOString()
  operation.retryCount++
  await updateOperation(operation)

  try {
    let url: string
    let body: Record<string, unknown>

    switch (operation.type) {
      case 'checkout':
        url = `${API_BASE}/staff/circulation/checkout`
        body = {
          patron_barcode: operation.patronIdentifier,
          item_barcode: operation.itemBarcode,
          offline_timestamp: operation.timestamp,
        }
        break
      case 'checkin':
        url = `${API_BASE}/staff/circulation/checkin`
        body = {
          item_barcode: operation.itemBarcode,
          offline_timestamp: operation.timestamp,
        }
        break
      case 'renew':
        url = `${API_BASE}/staff/circulation/renew`
        body = {
          patron_barcode: operation.patronIdentifier,
          item_barcode: operation.itemBarcode,
          offline_timestamp: operation.timestamp,
        }
        break
    }

    // eslint-disable-next-line no-restricted-syntax -- offline queue: uses caller-supplied token (not global tokenStore), inspects response.status for 409 conflict vs retry, and tolerates non-JSON error bodies
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    })

    if (response.ok) {
      const data = await response.json()
      operation.status = 'synced'
      operation.serverResponse = data
      operation.error = null
      await updateOperation(operation)
      return { operation, success: true }
    }

    // Handle conflict (item already checked out/in by someone else)
    if (response.status === 409) {
      operation.status = 'conflict'
      operation.error = 'Conflict: This item was already processed by another staff member.'
      operation.serverResponse = await response.json().catch(() => null)
      await updateOperation(operation)
      return { operation, success: false, conflict: true, error: operation.error }
    }

    // Handle other errors
    const errorText = await response.text().catch(() => 'a sync issue')
    if (operation.retryCount >= MAX_RETRIES) {
      operation.status = 'failed'
      operation.error = `Failed after ${MAX_RETRIES} attempts: ${errorText}`
    } else {
      operation.status = 'pending' // Will retry
      operation.error = errorText
    }
    await updateOperation(operation)
    return { operation, success: false, error: errorText }
  } catch (error: unknown) {
    const errorMsg = error instanceof Error ? error.message : 'Network error'
    if (operation.retryCount >= MAX_RETRIES) {
      operation.status = 'failed'
      operation.error = `Failed after ${MAX_RETRIES} attempts: ${errorMsg}`
    } else {
      operation.status = 'pending'
      operation.error = errorMsg
    }
    await updateOperation(operation)
    return { operation, success: false, error: errorMsg }
  }
}

export async function syncAllPending(token: string): Promise<SyncResult[]> {
  const pending = await getPendingOperations()
  const results: SyncResult[] = []

  for (const operation of pending) {
    const result = await syncOperation(operation, token)
    results.push(result)

    // If we hit a network error, stop trying remaining operations
    if (!result.success && !result.conflict && !navigator.onLine) {
      break
    }
  }

  return results
}

export function generateOfflineReceipt(
  operations: OfflineOperation[],
  patronName: string,
): string {
  const now = new Date()
  const lines: string[] = [
    '================================',
    '    LIBRARY SERVICE CENTER',
    '     OFFLINE CHECKOUT RECEIPT',
    '================================',
    '',
    `Patron: ${patronName}`,
    `Date: ${now.toLocaleDateString()}`,
    `Time: ${now.toLocaleTimeString()}`,
    '',
    '--- Items ---',
  ]

  for (const op of operations) {
    lines.push(`  ${op.type.toUpperCase()}: ${op.itemBarcode}`)
    lines.push(`    Queued: ${new Date(op.timestamp).toLocaleTimeString()}`)
  }

  lines.push('')
  lines.push('NOTE: These transactions were processed')
  lines.push('offline and will be synced when the')
  lines.push('network connection is restored.')
  lines.push('')
  lines.push('================================')

  return lines.join('\n')
}