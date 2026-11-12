/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// ==================== Types ====================

export interface CachedPatron {
  barcode: string
  id: number
  name: string
  photo_url: string | null
  status: string
  checkout_count: number
  checkout_limit: number
  card_expiry: string | null
  cached_at: string
}

export interface CachedItem {
  barcode: string
  id: number
  title: string
  author: string
  status: string
  branch_id: number
  call_number: string | null
  media_type: string
  cached_at: string
}

// ==================== Constants ====================

const DB_NAME = 'lsc-offline-cache'
const DB_VERSION = 1
const PATRON_STORE = 'patrons'
const ITEM_STORE = 'items'

// ==================== IndexedDB Helpers ====================

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result

      if (!db.objectStoreNames.contains(PATRON_STORE)) {
        db.createObjectStore(PATRON_STORE, { keyPath: 'barcode' })
      }
      if (!db.objectStoreNames.contains(ITEM_STORE)) {
        db.createObjectStore(ITEM_STORE, { keyPath: 'barcode' })
      }
    }
  })
}

// ==================== Patron Operations ====================

export async function lookupPatron(barcode: string): Promise<CachedPatron | null> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(PATRON_STORE, 'readonly')
    const store = tx.objectStore(PATRON_STORE)
    const request = store.get(barcode)

    request.onsuccess = () => resolve((request.result as CachedPatron) ?? null)
    request.onerror = () => reject(request.error)
    tx.oncomplete = () => db.close()
  })
}

export async function upsertPatron(patron: CachedPatron): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(PATRON_STORE, 'readwrite')
    const store = tx.objectStore(PATRON_STORE)
    const request = store.put(patron)

    request.onsuccess = () => resolve()
    request.onerror = () => reject(request.error)
    tx.oncomplete = () => db.close()
  })
}

export async function bulkUpsertPatrons(patrons: Omit<CachedPatron, 'cached_at'>[]): Promise<void> {
  const now = new Date().toISOString()
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(PATRON_STORE, 'readwrite')
    const store = tx.objectStore(PATRON_STORE)

    for (const patron of patrons) {
      store.put({ ...patron, cached_at: now })
    }

    tx.oncomplete = () => { db.close(); resolve() }
    tx.onerror = () => reject(tx.error)
  })
}

export async function incrementPatronCheckouts(barcode: string): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(PATRON_STORE, 'readwrite')
    const store = tx.objectStore(PATRON_STORE)
    const getRequest = store.get(barcode)

    getRequest.onsuccess = () => {
      const patron = getRequest.result as CachedPatron | undefined
      if (!patron) { resolve(); return }
      patron.checkout_count++
      store.put(patron)
    }
    getRequest.onerror = () => reject(getRequest.error)
    tx.oncomplete = () => { db.close(); resolve() }
    tx.onerror = () => reject(tx.error)
  })
}

export async function decrementPatronCheckouts(barcode: string): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(PATRON_STORE, 'readwrite')
    const store = tx.objectStore(PATRON_STORE)
    const getRequest = store.get(barcode)

    getRequest.onsuccess = () => {
      const patron = getRequest.result as CachedPatron | undefined
      if (!patron) { resolve(); return }
      patron.checkout_count = Math.max(0, patron.checkout_count - 1)
      store.put(patron)
    }
    getRequest.onerror = () => reject(getRequest.error)
    tx.oncomplete = () => { db.close(); resolve() }
    tx.onerror = () => reject(tx.error)
  })
}

// ==================== Item Operations ====================

export async function lookupItem(barcode: string): Promise<CachedItem | null> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ITEM_STORE, 'readonly')
    const store = tx.objectStore(ITEM_STORE)
    const request = store.get(barcode)

    request.onsuccess = () => resolve((request.result as CachedItem) ?? null)
    request.onerror = () => reject(request.error)
    tx.oncomplete = () => db.close()
  })
}

export async function upsertItem(item: CachedItem): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ITEM_STORE, 'readwrite')
    const store = tx.objectStore(ITEM_STORE)
    const request = store.put(item)

    request.onsuccess = () => resolve()
    request.onerror = () => reject(request.error)
    tx.oncomplete = () => db.close()
  })
}

export async function bulkUpsertItems(items: Omit<CachedItem, 'cached_at'>[]): Promise<void> {
  const now = new Date().toISOString()
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ITEM_STORE, 'readwrite')
    const store = tx.objectStore(ITEM_STORE)

    for (const item of items) {
      store.put({ ...item, cached_at: now })
    }

    tx.oncomplete = () => { db.close(); resolve() }
    tx.onerror = () => reject(tx.error)
  })
}

export async function markItemCheckedOut(barcode: string): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ITEM_STORE, 'readwrite')
    const store = tx.objectStore(ITEM_STORE)
    const getRequest = store.get(barcode)

    getRequest.onsuccess = () => {
      const item = getRequest.result as CachedItem | undefined
      if (!item) { resolve(); return }
      item.status = 'checked_out'
      store.put(item)
    }
    getRequest.onerror = () => reject(getRequest.error)
    tx.oncomplete = () => { db.close(); resolve() }
    tx.onerror = () => reject(tx.error)
  })
}

export async function markItemAvailable(barcode: string): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ITEM_STORE, 'readwrite')
    const store = tx.objectStore(ITEM_STORE)
    const getRequest = store.get(barcode)

    getRequest.onsuccess = () => {
      const item = getRequest.result as CachedItem | undefined
      if (!item) { resolve(); return }
      item.status = 'available'
      store.put(item)
    }
    getRequest.onerror = () => reject(getRequest.error)
    tx.oncomplete = () => { db.close(); resolve() }
    tx.onerror = () => reject(tx.error)
  })
}

// ==================== Utility ====================

export async function getCacheStats(): Promise<{ patrons: number; items: number }> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction([PATRON_STORE, ITEM_STORE], 'readonly')
    const patronCount = tx.objectStore(PATRON_STORE).count()
    const itemCount = tx.objectStore(ITEM_STORE).count()
    let patrons = 0
    let items = 0

    patronCount.onsuccess = () => { patrons = patronCount.result }
    itemCount.onsuccess = () => { items = itemCount.result }
    patronCount.onerror = () => reject(patronCount.error)
    itemCount.onerror = () => reject(itemCount.error)
    tx.oncomplete = () => { db.close(); resolve({ patrons, items }) }
    tx.onerror = () => reject(tx.error)
  })
}

export async function clearCache(): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction([PATRON_STORE, ITEM_STORE], 'readwrite')

    tx.objectStore(PATRON_STORE).clear()
    tx.objectStore(ITEM_STORE).clear()

    tx.oncomplete = () => { db.close(); resolve() }
    tx.onerror = () => reject(tx.error)
  })
}

export async function ensurePersistentStorage(): Promise<boolean> {
  if (navigator.storage?.persist) {
    return navigator.storage.persist()
  }
  return false
}
