/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Tracks recently viewed patrons per-staff-user in sessionStorage.
// Clears on tab close (intentional -- the circ desk is not a long-lived
// session and we don't want shared workstations bleeding history).

export interface RecentPatronEntry {
  id: number
  displayName: string
  viewedAt: string
}

const MAX_ENTRIES = 5

function storageKey(userId: number | null | undefined): string | null {
  if (userId == null) return null
  return `recent-patrons:${userId}`
}

export function readRecentPatrons(userId: number | null | undefined): RecentPatronEntry[] {
  const key = storageKey(userId)
  if (!key) return []
  try {
    const raw = sessionStorage.getItem(key)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter((e): e is RecentPatronEntry =>
        !!e && typeof e === "object" &&
        typeof (e as RecentPatronEntry).id === "number" &&
        typeof (e as RecentPatronEntry).displayName === "string" &&
        typeof (e as RecentPatronEntry).viewedAt === "string"
      )
      .slice(0, MAX_ENTRIES)
  } catch {
    return []
  }
}

export function recordRecentPatron(
  userId: number | null | undefined,
  entry: { id: number; displayName: string }
): RecentPatronEntry[] {
  const key = storageKey(userId)
  if (!key) return []
  const existing = readRecentPatrons(userId).filter((e) => e.id !== entry.id)
  const next: RecentPatronEntry[] = [
    { id: entry.id, displayName: entry.displayName, viewedAt: new Date().toISOString() },
    ...existing,
  ].slice(0, MAX_ENTRIES)
  try {
    sessionStorage.setItem(key, JSON.stringify(next))
  } catch {
    // sessionStorage full or unavailable -- non-fatal
  }
  return next
}
