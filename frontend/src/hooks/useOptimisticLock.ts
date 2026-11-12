/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useCallback, useEffect } from 'react'
import { fetchApi } from '@/lib/api-client'

export interface ConflictData {
  serverUpdatedAt: string
  localUpdatedAt: string
}

interface OptimisticLockResult {
  isStale: boolean
  conflictData: ConflictData | null
  checkForConflict: () => Promise<boolean>
  clearConflict: () => void
  forceSave: () => void
}

export function useOptimisticLock(
  entityType: string,
  entityId: number | null,
  updatedAt: string | null,
): OptimisticLockResult {
  const [isStale, setIsStale] = useState(false)
  const [conflictData, setConflictData] = useState<ConflictData | null>(null)
  const localTimestamp = useRef<string | null>(null)
  const forceRef = useRef(false)

  // Capture the timestamp when the entity is loaded / changes
  useEffect(() => {
    localTimestamp.current = updatedAt ?? null
    setIsStale(false)
    setConflictData(null)
    forceRef.current = false
  }, [entityId, updatedAt])

  const checkForConflict = useCallback(async (): Promise<boolean> => {
    // No conflict possible on create or when force-saving
    if (!entityId || !localTimestamp.current || forceRef.current) {
      return false
    }

    try {
      const current = await fetchApi<{ updated_at: string | null }>(
        `/${entityType}/${entityId}`,
      )

      if (
        current.updated_at &&
        current.updated_at !== localTimestamp.current
      ) {
        setIsStale(true)
        setConflictData({
          serverUpdatedAt: current.updated_at,
          localUpdatedAt: localTimestamp.current,
        })
        return true
      }
    } catch {
      // If we can't verify, let the save proceed --
      // the backend will catch real conflicts via its own checks.
    }

    return false
  }, [entityType, entityId])

  const clearConflict = useCallback(() => {
    setIsStale(false)
    setConflictData(null)
    forceRef.current = false
  }, [])

  const forceSave = useCallback(() => {
    forceRef.current = true
    setIsStale(false)
    setConflictData(null)
  }, [])

  return { isStale, conflictData, checkForConflict, clearConflict, forceSave }
}
