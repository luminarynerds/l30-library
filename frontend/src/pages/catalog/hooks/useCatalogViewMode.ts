/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable no-empty */
import { useState, useEffect, useCallback } from 'react'

type ViewMode = 'list' | 'grid'

const VIEW_MODE_KEY = 'lsc-catalog-view-mode'

export function useCatalogViewMode(quietMode: boolean) {
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    try {
      const saved = localStorage.getItem(VIEW_MODE_KEY)
      if (saved === 'grid' || saved === 'list') return saved
    } catch {}
    return 'list'
  })

  // Persist to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(VIEW_MODE_KEY, viewMode)
    } catch {}
  }, [viewMode])

  // Force list view when quiet mode is enabled
  const effectiveViewMode: ViewMode = quietMode ? 'list' : viewMode

  const setView = useCallback((mode: ViewMode) => {
    if (!quietMode) {
      setViewMode(mode)
    }
  }, [quietMode])

  return {
    viewMode: effectiveViewMode,
    setViewMode: setView,
    isGridDisabled: quietMode,
  }
}
