/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Schema-driven URL <-> filters codec. Phase 2 of the filtersSchema refactor.
 *
 * Replaces the hand-written URL parse/serialize blocks in
 * `useCatalogSearch.ts`. Behavior-preserving against the legacy
 * implementation; per-filter quirks (status enum gating, year parseInt
 * round-trip, language slice cap) are kept exactly as the audit documented.
 *
 * Non-filter URL params (`q`, `subject`, `sort`, `sort_dir`, `saved`) stay
 * owned by the hook; this module only knows about filter and sibling-bool
 * fields declared in `schema.ts`.
 */
import {
  filterSchema,
  siblingBoolSchema,
  type FilterValueType,
  type SiblingBoolDef,
} from './schema'
import type { CatalogFilters, CatalogSiblingBools } from './types'

/** Filter URL params the hook treats as "explicit user intent" — when any is
 * present, localStorage hydration is skipped on mount. Sort params and the
 * standalone `q`/`is_new` are also part of the legacy guard. */
const NON_FILTER_HAS_URL_KEYS = ['q', 'sort', 'sort_dir'] as const

// ---------- per-filter URL parsers ----------
//
// Most filters parse trivially by value-type. The exceptions (status enum
// gate, year/lexile parseInt, language slice) live here so the rest of the
// codec stays a flat schema iteration. Adding a new filter usually requires
// nothing in this table.

type FilterUrlReader = (raw: string) => unknown

const FILTER_URL_READERS: Partial<Record<string, FilterUrlReader>> = {
  // parseInt round-trip: drops NaN, normalizes `2026.5` -> `'2026'`.
  year_min: (raw) => {
    const n = parseInt(raw, 10)
    return Number.isNaN(n) ? undefined : String(n)
  },
  year_max: (raw) => {
    const n = parseInt(raw, 10)
    return Number.isNaN(n) ? undefined : String(n)
  },
  min_lexile: (raw) => {
    const n = parseInt(raw, 10)
    return Number.isNaN(n) ? undefined : n
  },
  max_lexile: (raw) => {
    const n = parseInt(raw, 10)
    return Number.isNaN(n) ? undefined : n
  },
  // Length cap matches the localStorage validator. ISO 639-2/B codes are
  // 3 chars, but historical saved searches occasionally carried locale tags.
  language: (raw) => raw.slice(0, 10),
}

const defaultUrlReader = (valueType: FilterValueType, raw: string): unknown => {
  switch (valueType) {
    case 'string':
    case 'string-nullable':
      return raw
    case 'number-nullable': {
      const n = parseInt(raw, 10)
      return Number.isNaN(n) ? undefined : n
    }
    case 'string-array':
      // ``string-array`` filters are handled inline in ``parseFiltersFromUrl``
      // via ``params.getAll``; never reach the scalar default path.
      return undefined
    case 'boolean':
      // Only ``true`` round-trips; any other value (including the explicit
      // string ``false``) is treated as URL-absent so the default false wins.
      return raw === 'true' ? true : undefined
  }
}

export function parseFiltersFromUrl(params: URLSearchParams): Partial<CatalogFilters> {
  const result: Partial<Record<string, unknown>> = {}
  for (const def of filterSchema) {
    if (!def.url) continue
    const candidateKeys = [def.url.key, ...(def.url.aliases ?? [])]

    // ``string-array`` filters round-trip as repeated URL params; read them
    // with ``getAll`` from every candidate key, drop blanks, and only set
    // when at least one value is present. Previously these were written to
    // the URL by the hook but never read back, silently emptying the chip
    // set on reload or deep-link share.
    if (def.valueType === 'string-array') {
      const collected: string[] = []
      for (const k of candidateKeys) {
        for (const v of params.getAll(k)) {
          if (v !== '') collected.push(v)
        }
      }
      if (collected.length > 0) result[def.name] = collected.slice(0, 20)
      continue
    }

    let raw: string | null = null
    for (const k of candidateKeys) {
      const v = params.get(k)
      if (v !== null) { raw = v; break }
    }
    if (raw === null) continue
    const reader = FILTER_URL_READERS[def.name] ?? ((s: string) => defaultUrlReader(def.valueType, s))
    const parsed = reader(raw)
    if (parsed === undefined) continue
    result[def.name] = parsed
  }
  return result as Partial<CatalogFilters>
}

export function parseSiblingBoolsFromUrl(params: URLSearchParams): Partial<CatalogSiblingBools> {
  const result: Partial<Record<string, boolean>> = {}
  for (const def of siblingBoolSchema) {
    if (!def.url) continue
    const raw = params.get(def.url.key)
    if (raw === null) continue
    result[def.name] = raw === 'true'
  }
  return result as Partial<CatalogSiblingBools>
}

export function hasAnyFilterUrlParam(params: URLSearchParams): boolean {
  for (const def of filterSchema) {
    if (!def.url) continue
    if (params.has(def.url.key)) return true
    for (const alias of def.url.aliases ?? []) {
      if (params.has(alias)) return true
    }
  }
  for (const def of siblingBoolSchema) {
    if (def.url && params.has(def.url.key)) return true
  }
  for (const k of NON_FILTER_HAS_URL_KEYS) {
    if (params.has(k)) return true
  }
  return false
}

// ---------- per-filter URL serializers ----------

type FilterUrlWriter = (value: unknown) => string | undefined

const FILTER_URL_WRITERS: Partial<Record<string, FilterUrlWriter>> = {}

const defaultUrlWriter = (
  valueType: FilterValueType,
  emptyAs: string | undefined,
  value: unknown,
): string | undefined => {
  if (emptyAs !== undefined && value === emptyAs) return undefined
  switch (valueType) {
    case 'string':
    case 'string-nullable':
      return value && typeof value === 'string' ? value : undefined
    case 'number-nullable':
      return typeof value === 'number' && Number.isFinite(value) ? String(value) : undefined
    case 'string-array':
      // Arrays are written inline in ``serializeFiltersToUrl`` via repeated
      // ``append`` calls; never reach the scalar default writer path.
      return undefined
    case 'boolean':
      // Booleans collapse to URL-absent when false so default state stays clean.
      return value === true ? 'true' : undefined
  }
}

export function serializeFiltersToUrl(filters: CatalogFilters, params: URLSearchParams): void {
  for (const def of filterSchema) {
    if (!def.url) continue

    // Multi-select facets clear any existing values for the key first, then
    // append one entry per array element. Without the delete, repeated
    // ``serializeFiltersToUrl`` calls would accumulate stale facet values on
    // the same key.
    if (def.valueType === 'string-array') {
      params.delete(def.url.key)
      const arr = (filters as Record<string, unknown>)[def.name]
      if (Array.isArray(arr)) {
        for (const v of arr) {
          if (typeof v === 'string' && v !== '') {
            params.append(def.url.key, v)
          }
        }
      }
      continue
    }

    const writer = FILTER_URL_WRITERS[def.name] ?? ((v: unknown) => defaultUrlWriter(def.valueType, def.url?.emptyAs, v))
    const written = writer((filters as Record<string, unknown>)[def.name])
    if (written === undefined) continue
    params.set(def.url.key, written)
  }
}

export function serializeSiblingBoolsToUrl(
  bools: CatalogSiblingBools,
  params: URLSearchParams,
): void {
  for (const def of siblingBoolSchema as readonly SiblingBoolDef[]) {
    if (!def.url) continue
    const v = (bools as Record<string, boolean>)[def.name]
    if (!v) continue
    params.set(def.url.key, 'true')
  }
}
