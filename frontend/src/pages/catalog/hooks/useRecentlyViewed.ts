/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useState } from 'react'
import * as Sentry from "@/lib/sentry-lazy"

const STORAGE_KEY = 'l30:recently-viewed-catalog-items'
const MAX_ENTRIES = 12

export function useRecentlyViewed() {
  const [ids, setIds] = useState<number[]>(() => readIds())

  // Cross-tab sync: another tab visiting an item updates the strip here too.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) setIds(readIds())
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const add = useCallback((id: number) => {
    if (!Number.isFinite(id) || id <= 0) return
    setIds((prev) => {
      const next = [id, ...prev.filter((existing) => existing !== id)].slice(0, MAX_ENTRIES)
      writeIds(next)
      return next
    })
  }, [])

  const clear = useCallback(() => {
    writeIds([])
    setIds([])
  }, [])

  return { ids, add, clear }
}

function readIds(): number[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter((v): v is number => typeof v === 'number' && Number.isFinite(v) && v > 0)
      .slice(0, MAX_ENTRIES)
  } catch (err) {
    Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    return []
  }
}

function writeIds(ids: number[]): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids))
  } catch (err) {
    // Quota exceeded or storage disabled (private browsing on some browsers).
    Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
  }
}
