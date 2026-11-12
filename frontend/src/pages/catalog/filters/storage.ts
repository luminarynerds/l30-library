/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Schema-driven localStorage <-> filters codec. Phase 2 of the filtersSchema
 * refactor.
 *
 * The storage shape is:
 *   { filters: { item_type, status, ... }, showNewArrivals, showLargePrintOnly,
 *     simplifiedView, sortBy, sortDirection }
 *
 * This module owns the `filters` sub-object plus the two sibling booleans;
 * the hook continues to own `simplifiedView`, `sortBy`, and `sortDirection`
 * which are not catalog filters.
 *
 * Behavior matches the legacy validator in `useCatalogSearch.ts` (lines
 * 165-189 of the legacy file) including the `topic: ya -> young_adult`
 * migration and per-field length caps.
 */
import { filterSchema, siblingBoolSchema } from './schema'
import type { CatalogFilters, CatalogSiblingBools } from './types'
import { EMPTY_FILTERS, EMPTY_SIBLING_BOOLS } from './types'

// Per-filter coercion for the handful of fields that can't be handled by
// value-type + maxLength alone. Migrations belong here, not in the schema,
// because they describe one-shot data fixes rather than steady-state shape.
type FilterStorageReader = (raw: unknown) => unknown

const FILTER_STORAGE_READERS: Partial<Record<string, FilterStorageReader>> = {
  // Legacy facet rename: stored value `ya` now maps to `young_adult`. Keep
  // until enough patrons have re-saved searches that the rename has rolled
  // through. Removal tied to phase 6 cleanup.
  topic: (raw) => {
    if (typeof raw !== 'string') return undefined
    return raw === 'ya' ? 'young_adult' : raw
  },
}

export function readFiltersFromStorage(rawFilters: unknown): CatalogFilters {
  if (typeof rawFilters !== 'object' || rawFilters === null) {
    return { ...EMPTY_FILTERS }
  }
  const source = rawFilters as Record<string, unknown>
  const result: Record<string, unknown> = { ...EMPTY_FILTERS }
  for (const def of filterSchema) {
    const raw = source[def.name]
    if (raw === undefined) continue

    const reader = FILTER_STORAGE_READERS[def.name]
    if (reader) {
      const coerced = reader(raw)
      if (coerced !== undefined) result[def.name] = coerced
      continue
    }

    switch (def.valueType) {
      case 'string':
      case 'string-nullable': {
        if (typeof raw !== 'string') break
        const capped = def.ls.maxLength ? raw.slice(0, def.ls.maxLength) : raw
        result[def.name] = capped
        break
      }
      case 'number-nullable': {
        if (typeof raw !== 'number' || !Number.isFinite(raw)) break
        result[def.name] = raw
        break
      }
      case 'boolean': {
        if (typeof raw !== 'boolean') break
        result[def.name] = raw
        break
      }
      case 'string-array': {
        if (!Array.isArray(raw)) break
        result[def.name] = raw.filter((v): v is string => typeof v === 'string')
        break
      }
    }
  }
  return result as CatalogFilters
}

export function readSiblingBoolsFromStorage(rawPrefs: unknown): CatalogSiblingBools {
  if (typeof rawPrefs !== 'object' || rawPrefs === null) {
    return { ...EMPTY_SIBLING_BOOLS }
  }
  const source = rawPrefs as Record<string, unknown>
  const result: Record<string, boolean> = { ...EMPTY_SIBLING_BOOLS }
  for (const def of siblingBoolSchema) {
    const raw = source[def.name]
    if (typeof raw === 'boolean') result[def.name] = raw
  }
  return result as CatalogSiblingBools
}

export function writeFiltersToStorage(filters: CatalogFilters): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const def of filterSchema) {
    out[def.name] = (filters as Record<string, unknown>)[def.name]
  }
  return out
}

export function writeSiblingBoolsToStorage(bools: CatalogSiblingBools): Record<string, boolean> {
  const out: Record<string, boolean> = {}
  for (const def of siblingBoolSchema) {
    out[def.name] = bools[def.name as keyof CatalogSiblingBools] ?? false
  }
  return out
}
