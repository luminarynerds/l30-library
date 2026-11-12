/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState, useCallback } from 'react'

export type AutoSaveStatus = 'idle' | 'saving' | 'saved' | 'error'

interface UseAutoSaveOptions<T> {
  data: T
  onSave: (data: T) => Promise<void>
  delay?: number // milliseconds to wait after last change before saving
  enabled?: boolean
}

interface UseAutoSaveReturn {
  status: AutoSaveStatus
  lastSaved: Date | null
  error: Error | null
  forceSave: () => Promise<void>
}

export function useAutoSave<T>({
  data,
  onSave,
  delay = 2000,
  enabled = true
}: UseAutoSaveOptions<T>): UseAutoSaveReturn {
  const [status, setStatus] = useState<AutoSaveStatus>('idle')
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const timeoutRef = useRef<NodeJS.Timeout>()
  const previousDataRef = useRef<T>(data)
  const isMountedRef = useRef(true)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  const save = useCallback(async () => {
    if (!enabled) return

    setStatus('saving')
    setError(null)

    try {
      await onSave(data)

      if (isMountedRef.current) {
        setStatus('saved')
        setLastSaved(new Date())
        previousDataRef.current = data

        // Reset to idle after 3 seconds
        setTimeout(() => {
          if (isMountedRef.current) {
            setStatus('idle')
          }
        }, 3000)
      }
    } catch (_err) {
      if (isMountedRef.current) {
        setStatus('error')
        setError(_err as Error)
      }
    }
  }, [data, onSave, enabled])

  const forceSave = useCallback(async () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    await save()
  }, [save])

  // When autosave flips from disabled -> enabled (e.g. a record finishes loading
  // and the form becomes editable), re-baseline to the current data so the
  // initial load is not mistaken for an edit. Without this, merely opening a
  // record triggers a spurious save (round-tripping content on view).
  const prevEnabledRef = useRef(enabled)
  useEffect(() => {
    if (enabled && !prevEnabledRef.current) {
      previousDataRef.current = data
    }
    prevEnabledRef.current = enabled
  }, [enabled, data])

  // Auto-save effect
  useEffect(() => {
    if (!enabled) return

    // Check if data actually changed
    const dataChanged = JSON.stringify(data) !== JSON.stringify(previousDataRef.current)

    if (!dataChanged) return

    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    // Set new timeout
    timeoutRef.current = setTimeout(() => {
      save()
    }, delay)

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [data, delay, enabled, save])

  return {
    status,
    lastSaved,
    error,
    forceSave
  }
}
