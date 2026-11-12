/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useState } from 'react'

function readInitial(storageKey: string): Set<string> {
  if (typeof window === 'undefined') return new Set()
  try {
    const raw = window.sessionStorage.getItem(storageKey)
    if (!raw) return new Set()
    const parsed: unknown = JSON.parse(raw)
    if (Array.isArray(parsed)) return new Set(parsed.filter((x): x is string => typeof x === 'string'))
  } catch {
    // ignore corrupt storage
  }
  return new Set()
}

export function useExpandedSet(storageKey: string): {
  expanded: Set<string>
  toggle: (name: string) => void
} {
  const [expanded, setExpanded] = useState<Set<string>>(() => readInitial(storageKey))

  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      window.sessionStorage.setItem(storageKey, JSON.stringify([...expanded]))
    } catch {
      // storage may be unavailable (private mode, quota); silently no-op
    }
  }, [expanded, storageKey])

  const toggle = useCallback((name: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }, [])

  return { expanded, toggle }
}
