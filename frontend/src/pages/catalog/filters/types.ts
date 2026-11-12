/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Derived types for the catalog filter schema. Phase 1: parallel to the
 * hand-written interface in `pages/catalog/utils/catalogFilters.ts`; later
 * phases replace the hand-written one with this.
 */
import { filterSchema, siblingBoolSchema } from './schema'
import type { FilterSchema, FilterValueTypeMap, SiblingBoolSchema } from './schema'

export type SchemaToFilters<T extends FilterSchema> = {
  [F in T[number] as F['name']]: FilterValueTypeMap[F['valueType']]
}

export type CatalogFilters = SchemaToFilters<FilterSchema>

export type SchemaToSiblingBools<T extends SiblingBoolSchema> = {
  [B in T[number] as B['name']]: boolean
}

export type CatalogSiblingBools = SchemaToSiblingBools<SiblingBoolSchema>

/**
 * `EMPTY_FILTERS` derived from the schema. Equivalent to the hand-written
 * constant in `catalogFilters.ts`.
 */
export const EMPTY_FILTERS: CatalogFilters = Object.fromEntries(
  filterSchema.map((f) => [f.name, f.default]),
) as CatalogFilters

export const EMPTY_SIBLING_BOOLS: CatalogSiblingBools = Object.fromEntries(
  siblingBoolSchema.map((b) => [b.name, b.default]),
) as CatalogSiblingBools
