/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef } from 'react'

type ViewMode = 'list' | 'grid'

interface SavedState {
  scrollY: number
  isDrawerOpen: boolean
  viewMode: ViewMode
}

interface Options {
  /** Restore is gated until results are ready so window has enough height. */
  resultsReady: boolean
  isDrawerOpen: boolean
  setIsDrawerOpen: (v: boolean) => void
  viewMode: ViewMode
  setViewMode: (m: ViewMode) => void
}

function storageKey(): string {
  return `catalog-state:${typeof window === 'undefined' ? '' : window.location.pathname}`
}

function readState(): SavedState | null {
  try {
    const raw = sessionStorage.getItem(storageKey())
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<SavedState>
    if (
      typeof parsed.scrollY !== 'number' ||
      typeof parsed.isDrawerOpen !== 'boolean' ||
      (parsed.viewMode !== 'list' && parsed.viewMode !== 'grid')
    ) {
      return null
    }
    return parsed as SavedState
  } catch {
    return null
  }
}

function writeState(state: SavedState): void {
  try {
    sessionStorage.setItem(storageKey(), JSON.stringify(state))
  } catch {
    // private mode / quota — silently drop
  }
}

export function useCatalogPageStateRestore({
  resultsReady,
  isDrawerOpen,
  setIsDrawerOpen,
  viewMode,
  setViewMode,
}: Options): void {
  // Track latest values so unmount/unload reads the current snapshot,
  // not the closure captured when the effect first ran.
  const latestRef = useRef({ isDrawerOpen, viewMode })
  latestRef.current = { isDrawerOpen, viewMode }

  const hasRestoredDrawerRef = useRef(false)
  const hasRestoredScrollRef = useRef(false)

  // Restore drawer + viewMode synchronously on mount (cheap state).
  useEffect(() => {
    if (hasRestoredDrawerRef.current) return
    hasRestoredDrawerRef.current = true
    const saved = readState()
    if (!saved) return
    if (saved.isDrawerOpen !== isDrawerOpen) setIsDrawerOpen(saved.isDrawerOpen)
    if (saved.viewMode !== viewMode) setViewMode(saved.viewMode)
    // Intentionally only on mount — restoring once is the contract.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Restore scroll only once results are in the DOM, otherwise the browser
  // caps scrollTo at current document height and silently no-ops.
  useEffect(() => {
    if (hasRestoredScrollRef.current) return
    if (!resultsReady) return
    const saved = readState()
    if (!saved) {
      hasRestoredScrollRef.current = true
      return
    }
    hasRestoredScrollRef.current = true
    // Two RAFs: first lets React commit, second lets layout settle.
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        window.scrollTo({ top: saved.scrollY, behavior: 'auto' })
      })
    })
  }, [resultsReady])

  // Save on unmount (SPA navigation) AND on beforeunload (tab close / hard refresh).
  useEffect(() => {
    const snapshot = (): SavedState => ({
      scrollY: window.scrollY,
      isDrawerOpen: latestRef.current.isDrawerOpen,
      viewMode: latestRef.current.viewMode,
    })
    const onBeforeUnload = () => writeState(snapshot())
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload)
      writeState(snapshot())
    }
  }, [])
}
