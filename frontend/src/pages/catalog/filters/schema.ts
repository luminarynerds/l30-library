/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Declarative catalog-filter schema (phase 1 of the filtersSchema refactor).
 *
 * Source of truth for every catalog filter. Later phases derive the URL codec,
 * localStorage codec, API request builder, sidebar UI, and backend mirror from
 * this one array. Adding a new filter = add one entry; no other site changes.
 *
 * Phase 1 invariant: ZERO runtime imports from production code. The schema and
 * its derived `CatalogFilters` type exist alongside the hand-written interface
 * in `pages/catalog/utils/catalogFilters.ts` until Phase 2 begins migrating
 * call sites.
 */

// ---------- value-type registry ----------

export type FilterValueTypeMap = {
  'string': string
  'string-nullable': string | null
  'number-nullable': number | null
  // Multi-select facets serialize as repeated URL params
  // (`?subject_facets=Fiction&subject_facets=Memoir`) and round-trip through
  // ``getAll`` / ``append`` rather than the scalar ``get`` / ``set`` path.
  'string-array': string[]
  // Boolean filters serialize as `key=true` (omitted when false). Used for
  // toggles like `available_only` (#887) and `available_for_hold` (#889).
  'boolean': boolean
}

export type FilterValueType = keyof FilterValueTypeMap

// ---------- scope ----------
//
// `server`      — backend has a predicate; filter participates in the SQL query.
// `client-post` — no backend predicate; FE filters the current page of results
//                 after fetch. Latent under-report bug past page 1 (issue #886).
// `dead`        — exists on the type/LS/sidebar but does nothing. Slated for
//                 removal in phase 6.
export type FilterScope = 'server' | 'client-post' | 'dead'

// ---------- URL serialization ----------

export type FilterUrlConfig = {
  /** Primary URL key written by the serializer. */
  key: string
  /** Additional URL keys the reader accepts (e.g. legacy `item_type` -> `type`). */
  aliases?: readonly string[]
  /** Value that the serializer treats as "absent" and omits from the URL. */
  emptyAs?: string
} | null

// ---------- localStorage ----------

export type FilterLsConfig = {
  /** Path under `prefs.filters.<key>` in the saved-search payload. */
  key: string
  /** Optional max length applied by the validator. */
  maxLength?: number
}

// ---------- API ----------

export type FilterApiConfig = {
  /** Backend `CatalogSearchParams` field name. */
  sendAs: string
} | null

// ---------- filter definition ----------

export interface FilterDef<
  Name extends string = string,
  VT extends FilterValueType = FilterValueType,
> {
  name: Name
  valueType: VT
  default: FilterValueTypeMap[VT]
  scope: FilterScope
  url: FilterUrlConfig
  ls: FilterLsConfig
  api: FilterApiConfig
  /**
   * True when the filter has a non-default value. Drives the active-chip
   * builder and the "any filter active?" guards.
   */
  isActive: (value: FilterValueTypeMap[VT]) => boolean
}

export function defineFilter<Name extends string, VT extends FilterValueType>(
  def: FilterDef<Name, VT>,
): FilterDef<Name, VT> {
  return def
}

// ---------- the schema ----------

const isNonEmptyString = (v: string | null): boolean => v !== null && v !== ''
const isPresentNumber = (v: number | null): boolean => v !== null

export const filterSchema = [
  defineFilter({
    name: 'item_type',
    valueType: 'string-nullable',
    default: '',
    scope: 'server',
    url: { key: 'item_type' },
    ls: { key: 'item_type' },
    api: { sendAs: 'item_type' },
    isActive: isNonEmptyString,
  }),
  defineFilter({
    name: 'available_only',
    valueType: 'boolean',
    default: false,
    scope: 'server',
    // #887 collapsed the previous faux-enum `status` field (only ever `''`
    // vs `'available'`) to a single boolean. The API client still maps this
    // to `status=available` on the wire to preserve the backend contract.
    // Serializer writes `available_only=true` only; false is URL-absent.
    url: { key: 'available_only' },
    ls: { key: 'available_only' },
    api: { sendAs: 'available_only' },
    isActive: (v) => v === true,
  }),
  defineFilter({
    name: 'available_for_hold',
    valueType: 'boolean',
    default: false,
    // #889 surfaces the backend `available_for_hold` Query param (see
    // backend/app/api/v1/catalog/browse.py:441). When true, returns only
    // items where placing a hold is meaningful (i.e. not lost, withdrawn,
    // missing, reference, or restricted). Different from `available_only`
    // (status=available) because a checked-out title is "holdable" but
    // not "available now".
    scope: 'server',
    url: { key: 'available_for_hold' },
    ls: { key: 'available_for_hold' },
    api: { sendAs: 'available_for_hold' },
    isActive: (v) => v === true,
  }),
  defineFilter({
    name: 'year_min',
    valueType: 'string',
    default: '',
    scope: 'server',
    url: { key: 'year_min' },
    ls: { key: 'year_min' },
    api: { sendAs: 'year_min' },
    isActive: (v) => v !== '',
  }),
  defineFilter({
    name: 'year_max',
    valueType: 'string',
    default: '',
    scope: 'server',
    url: { key: 'year_max' },
    ls: { key: 'year_max' },
    api: { sendAs: 'year_max' },
    isActive: (v) => v !== '',
  }),
  defineFilter({
    name: 'location',
    valueType: 'string',
    default: '',
    scope: 'server',
    // PR #941 closed issue #884: location now round-trips through the URL
    // so reload/share preserves the patron's filter selection.
    url: { key: 'location' },
    ls: { key: 'location', maxLength: 50 },
    api: { sendAs: 'location' },
    isActive: (v) => v !== '',
  }),
  defineFilter({
    name: 'publisher',
    valueType: 'string',
    default: '',
    // PR #945 closed issue #885: sidebar TextFilterInput now surfaces
    // publisher, and URL round-tripping preserves it on reload/share.
    scope: 'server',
    url: { key: 'publisher' },
    ls: { key: 'publisher', maxLength: 100 },
    api: { sendAs: 'publisher' },
    isActive: (v) => v !== '',
  }),
  defineFilter({
    name: 'reading_time',
    valueType: 'string',
    default: '',
    // #888: still client-post (no backend predicate), but the selection now
    // round-trips through the URL so reload/share preserves it.
    scope: 'client-post',
    url: { key: 'reading_time' },
    ls: { key: 'reading_time' },
    api: null,
    isActive: (v) => v !== '',
  }),
  defineFilter({
    name: 'access',
    valueType: 'string',
    default: '',
    // #888: URL-serialized; see reading_time above.
    scope: 'client-post',
    url: { key: 'access' },
    ls: { key: 'access' },
    api: null,
    isActive: (v) => v !== '',
  }),
  defineFilter({
    name: 'topic',
    valueType: 'string',
    default: '',
    // #888: URL-serialized; see reading_time above.
    scope: 'client-post',
    url: { key: 'topic' },
    ls: { key: 'topic' },
    api: null,
    isActive: (v) => v !== '',
  }),
  defineFilter({
    name: 'language',
    valueType: 'string',
    default: '',
    scope: 'server',
    url: { key: 'language' },
    ls: { key: 'language', maxLength: 10 },
    api: { sendAs: 'language' },
    isActive: (v) => v !== '',
  }),
  defineFilter({
    name: 'min_lexile',
    valueType: 'number-nullable',
    default: null,
    scope: 'server',
    url: { key: 'min_lexile' },
    ls: { key: 'min_lexile' },
    api: { sendAs: 'min_lexile' },
    isActive: isPresentNumber,
  }),
  defineFilter({
    name: 'max_lexile',
    valueType: 'number-nullable',
    default: null,
    scope: 'server',
    url: { key: 'max_lexile' },
    ls: { key: 'max_lexile' },
    api: { sendAs: 'max_lexile' },
    isActive: isPresentNumber,
  }),
  // Multi-select facets. Previously written to URL by hand inside
  // ``useCatalogSearch`` but never parsed back, so a reload/share silently
  // emptied the chip set. Routing them through the schema-driven codec
  // (``string-array`` value type, ``getAll`` reader, repeated ``append``
  // writer) closes that ghost-toggle case.
  defineFilter({
    name: 'subject_facets',
    valueType: 'string-array',
    default: [],
    scope: 'server',
    url: { key: 'subject_facets' },
    ls: { key: 'subject_facets' },
    api: { sendAs: 'subject_facets' },
    isActive: (v) => Array.isArray(v) && v.length > 0,
  }),
  defineFilter({
    name: 'author_facets',
    valueType: 'string-array',
    default: [],
    scope: 'server',
    url: { key: 'author_facets' },
    ls: { key: 'author_facets' },
    api: { sendAs: 'author_facets' },
    isActive: (v) => Array.isArray(v) && v.length > 0,
  }),
  defineFilter({
    name: 'series_facets',
    valueType: 'string-array',
    default: [],
    scope: 'server',
    url: { key: 'series_facets' },
    ls: { key: 'series_facets' },
    api: { sendAs: 'series_facets' },
    isActive: (v) => Array.isArray(v) && v.length > 0,
  }),
] as const

export type FilterSchema = typeof filterSchema
export type FilterName = FilterSchema[number]['name']

// ---------- sibling booleans ----------
//
// `showNewArrivals` and `showLargePrintOnly` are stored as sibling state in
// `useCatalogSearch`, not inside `CatalogFilters`. They follow the same
// schema-driven pattern but with a separate registry so the derived
// `CatalogFilters` type stays structurally identical to the legacy interface.

export interface SiblingBoolDef<Name extends string = string> {
  name: Name
  default: boolean
  scope: FilterScope
  url: FilterUrlConfig
  ls: { key: string }
  api: FilterApiConfig
}

export function defineSiblingBool<Name extends string>(
  def: SiblingBoolDef<Name>,
): SiblingBoolDef<Name> {
  return def
}

export const siblingBoolSchema = [
  defineSiblingBool({
    name: 'showNewArrivals',
    default: false,
    scope: 'server',
    url: { key: 'is_new' },
    ls: { key: 'showNewArrivals' },
    api: { sendAs: 'is_new' },
  }),
  defineSiblingBool({
    name: 'showLargePrintOnly',
    default: false,
    scope: 'server',
    // #888: URL-serialized as `is_large_print=true` so the toggle survives
    // reload / deep-link share. unified-search forwards is_large_print to
    // /search/unified, which honors it on the local source.
    url: { key: 'is_large_print' },
    ls: { key: 'showLargePrintOnly' },
    api: { sendAs: 'is_large_print' },
  }),
] as const

export type SiblingBoolSchema = typeof siblingBoolSchema
export type SiblingBoolName = SiblingBoolSchema[number]['name']
