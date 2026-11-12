/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

interface NetworkInformationLike {
  saveData?: boolean
  effectiveType?: 'slow-2g' | '2g' | '3g' | '4g' | string
}

function readConnection(): NetworkInformationLike | null {
  if (typeof navigator === 'undefined') return null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nav = navigator as any
  return (nav.connection || nav.mozConnection || nav.webkitConnection || null) as NetworkInformationLike | null
}

export function shouldAutoHideCoversForNetwork(): boolean {
  const conn = readConnection()
  if (!conn) return false
  if (conn.saveData === true) return true
  if (conn.effectiveType === '2g' || conn.effectiveType === 'slow-2g') return true
  return false
}

export function getInitialHideCovers(storageKey: string = 'catalog-hide-covers'): {
  value: boolean
  autoApplied: boolean
} {
  try {
    const stored = localStorage.getItem(storageKey)
    if (stored !== null) {
      return { value: stored === 'true', autoApplied: false }
    }
  } catch {
    // localStorage unavailable (private mode, sandboxed iframe) -- fall through.
  }
  const auto = shouldAutoHideCoversForNetwork()
  return { value: auto, autoApplied: auto }
}
