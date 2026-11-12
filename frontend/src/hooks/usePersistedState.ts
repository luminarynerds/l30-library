/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'

let uiStateCache: Record<string, unknown> | null = null
const pendingWrites = new Map<string, unknown>()
let flushTimer: ReturnType<typeof setTimeout> | null = null

async function fetchUIState(): Promise<Record<string, unknown>> {
  // Backend route not implemented yet -- use localStorage only
  if (uiStateCache === null) uiStateCache = {}
  return uiStateCache
}

function schedulePatchFlush() {
  if (flushTimer) return
  flushTimer = setTimeout(async () => {
    flushTimer = null
    if (pendingWrites.size === 0) return
    pendingWrites.clear()
    // Backend route not implemented -- localStorage is the only store
  }, 1000)
}

export function usePersistedState<T>(
  key: string,
  defaultValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const { isAuthenticated } = useAuth()
  const hasSyncedRef = useRef(false)

  const [value, setValueRaw] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key)
      if (stored !== null) return JSON.parse(stored) as T
    } catch { /* ignore: localStorage may be unavailable */ }
    return defaultValue
  })

  // On auth, fetch from API and override local value
  useEffect(() => {
    if (!isAuthenticated || hasSyncedRef.current) return
    hasSyncedRef.current = true
    fetchUIState().then((state) => {
      if (key in state) {
        const apiValue = state[key] as T
        setValueRaw(apiValue)
        try {
          localStorage.setItem(key, JSON.stringify(apiValue))
        } catch { /* ignore: localStorage may be unavailable */ }
      }
    })
  }, [isAuthenticated, key])

  // Reset sync flag on logout
  useEffect(() => {
    if (!isAuthenticated) {
      hasSyncedRef.current = false
    }
  }, [isAuthenticated])

  const setValue = useCallback(
    (update: T | ((prev: T) => T)) => {
      setValueRaw((prev) => {
        const next = typeof update === 'function' ? (update as (prev: T) => T)(prev) : update
        // Write to localStorage (sync cache)
        try {
          localStorage.setItem(key, JSON.stringify(next))
        } catch { /* ignore: localStorage may be unavailable */ }
        // Queue API write if authenticated
        if (isAuthenticated) {
          if (uiStateCache) uiStateCache[key] = next
          pendingWrites.set(key, next)
          schedulePatchFlush()
        }
        return next
      })
    },
    [key, isAuthenticated],
  )

  return [value, setValue]
}

export function clearUIStateCache() {
  uiStateCache = null
  pendingWrites.clear()
  if (flushTimer) {
    clearTimeout(flushTimer)
    flushTimer = null
  }
}
