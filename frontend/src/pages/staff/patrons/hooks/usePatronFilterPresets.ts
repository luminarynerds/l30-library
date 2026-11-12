/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useMemo, useState } from "react"
import type { FilterPreset, PatronAdvancedFilters } from "@/api/staff-api/patrons"
import type { StatusFilter } from "../types"

export const PATRON_PRESETS_VERSION = 1

const STORAGE_PREFIX = "patron-presets"

export type PresetFilters = PatronAdvancedFilters & { statusFilter?: StatusFilter }

export interface BuiltInPreset {
  id: string
  nameKey: string
  build: () => PresetFilters
}

// Built-ins map to the fields that currently exist in PatronAdvancedFilters.
// "Inactive 90d" and "Expiring 30d" have no backing filter field today and
// were substituted; see PR body and TODO below for context.
export const BUILTIN_PRESETS: BuiltInPreset[] = [
  {
    id: "builtin:has-overdue",
    nameKey: "staffPatrons.presets.builtin.hasOverdue",
    build: () => ({ hasOverdue: "has_overdue" }),
  },
  {
    id: "builtin:fines-over-5",
    nameKey: "staffPatrons.presets.builtin.finesOver5",
    build: () => ({ finesMin: 5 }),
  },
  {
    id: "builtin:blocked",
    nameKey: "staffPatrons.presets.builtin.blocked",
    build: () => ({ statusFilter: "blocked" }),
  },
  {
    // TODO: switch to cardStatus: 'expiring_30d' once cluster E lands.
    // No card-expiry or inactivity filter exists today, so we proxy
    // with "new this month" (members joined in the last 30 days).
    id: "builtin:new-this-month",
    nameKey: "staffPatrons.presets.builtin.newThisMonth",
    build: () => {
      const d = new Date()
      d.setDate(d.getDate() - 30)
      return { memberSinceFrom: d.toISOString().slice(0, 10) }
    },
  },
]

interface PersistedShape {
  version: number
  presets: FilterPreset[]
}

function storageKey(userId: number | string): string {
  return `${STORAGE_PREFIX}:${userId}`
}

function readUserPresets(userId: number | string | null | undefined): FilterPreset[] {
  if (userId === null || userId === undefined) return []
  try {
    const raw = window.localStorage.getItem(storageKey(userId))
    if (!raw) return []
    const parsed = JSON.parse(raw) as Partial<PersistedShape>
    if (!parsed || typeof parsed !== "object") return []
    if (parsed.version !== PATRON_PRESETS_VERSION) return []
    if (!Array.isArray(parsed.presets)) return []
    return parsed.presets.filter(
      (p): p is FilterPreset =>
        !!p && typeof p.id === "string" && typeof p.name === "string" && !!p.filters
    )
  } catch {
    return []
  }
}

function writeUserPresets(userId: number | string, presets: FilterPreset[]): void {
  try {
    const payload: PersistedShape = { version: PATRON_PRESETS_VERSION, presets }
    window.localStorage.setItem(storageKey(userId), JSON.stringify(payload))
  } catch {
    // Quota or unavailable storage — silently skip; in-memory state stays consistent.
  }
}

export interface UsePatronFilterPresetsResult {
  userPresets: FilterPreset[]
  activePresetId: string | null
  applyPreset: (id: string, filters: PresetFilters) => void
  clearActivePreset: () => void
  saveCurrentAsPreset: (name: string, filters: PresetFilters) => FilterPreset | null
  deleteUserPreset: (id: string) => void
}

export function usePatronFilterPresets(
  userId: number | string | null | undefined
): UsePatronFilterPresetsResult {
  // Track the userId we last hydrated against; if it changes, re-read from storage
  // in the same render (React's blessed pattern for derived state — no effect needed).
  const [lastUserId, setLastUserId] = useState<typeof userId>(userId)
  const [userPresets, setUserPresets] = useState<FilterPreset[]>(() => readUserPresets(userId))
  const [activePresetId, setActivePresetId] = useState<string | null>(null)

  if (lastUserId !== userId) {
    setLastUserId(userId)
    setUserPresets(readUserPresets(userId))
    setActivePresetId(null)
  }

  const applyPreset = useCallback((id: string, _filters: PresetFilters) => {
    setActivePresetId(id)
  }, [])

  const clearActivePreset = useCallback(() => {
    setActivePresetId(null)
  }, [])

  const saveCurrentAsPreset = useCallback(
    (name: string, filters: PresetFilters): FilterPreset | null => {
      if (userId === null || userId === undefined) return null
      const trimmed = name.trim()
      if (!trimmed) return null
      const preset: FilterPreset = {
        id: `user:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`,
        name: trimmed,
        filters,
        createdAt: new Date().toISOString(),
      }
      setUserPresets((prev) => {
        const next = [...prev, preset]
        writeUserPresets(userId, next)
        return next
      })
      setActivePresetId(preset.id)
      return preset
    },
    [userId]
  )

  const deleteUserPreset = useCallback(
    (id: string) => {
      if (userId === null || userId === undefined) return
      setUserPresets((prev) => {
        const next = prev.filter((p) => p.id !== id)
        writeUserPresets(userId, next)
        return next
      })
      setActivePresetId((current) => (current === id ? null : current))
    },
    [userId]
  )

  return useMemo(
    () => ({
      userPresets,
      activePresetId,
      applyPreset,
      clearActivePreset,
      saveCurrentAsPreset,
      deleteUserPreset,
    }),
    [userPresets, activePresetId, applyPreset, clearActivePreset, saveCurrentAsPreset, deleteUserPreset]
  )
}
