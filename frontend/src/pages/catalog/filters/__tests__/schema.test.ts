/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Type-level tests asserting the schema-derived `CatalogFilters` is
 * structurally identical to the hand-written interface in
 * `pages/catalog/utils/catalogFilters.ts`. If these fail to compile, the
 * schema and the legacy interface have drifted and downstream phases would
 * silently swap field types.
 */
import { describe, expect, it } from 'vitest'
import { CatalogFilters as LegacyCatalogFilters, EMPTY_FILTERS as LEGACY_EMPTY_FILTERS } from '../../utils/catalogFilters'
import {
  filterSchema,
  siblingBoolSchema,
  type FilterName,
  type SiblingBoolName,
} from '../schema'
import { EMPTY_FILTERS, EMPTY_SIBLING_BOOLS, type CatalogFilters } from '../types'

// ---------- type-equality machinery ----------
//
// Strict bidirectional structural equality. `Equal<A, B>` is `true` only when
// `A` and `B` are assignable to each other AND have the same keys with the
// same types. The `<T>() => T extends X ? 1 : 2` pattern is the standard
// invariant-position trick so that `string | null` and `string` are NOT equal.

type Equal<A, B> =
  (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2)
    ? true
    : false

function assertTrue<T extends true>(_?: T): void {}

describe('catalog filter schema — derived type equality', () => {
  it('derived CatalogFilters matches the legacy hand-written interface', () => {
    assertTrue<Equal<CatalogFilters, LegacyCatalogFilters>>()
  })

  it('EMPTY_FILTERS shape matches the legacy constant field-for-field', () => {
    expect(EMPTY_FILTERS).toStrictEqual(LEGACY_EMPTY_FILTERS)
  })

  it('every legacy field is represented in the schema exactly once', () => {
    const schemaNames = filterSchema.map((f) => f.name).sort()
    const legacyKeys = (Object.keys(LEGACY_EMPTY_FILTERS) as FilterName[]).sort()
    expect(schemaNames).toStrictEqual(legacyKeys)
    expect(new Set(schemaNames).size).toBe(schemaNames.length)
  })

  it('every schema default satisfies its declared value type', () => {
    for (const f of filterSchema) {
      switch (f.valueType) {
        case 'string':
          expect(typeof f.default).toBe('string')
          break
        case 'string-nullable':
          expect(f.default === null || typeof f.default === 'string').toBe(true)
          break
        case 'number-nullable':
          expect(f.default === null || typeof f.default === 'number').toBe(true)
          break
        case 'boolean':
          expect(typeof f.default).toBe('boolean')
          break
        case 'string-array':
          expect(Array.isArray(f.default)).toBe(true)
          break
      }
    }
  })

  it('sibling boolean registry covers both showNewArrivals and showLargePrintOnly', () => {
    const names = siblingBoolSchema.map((b) => b.name).sort()
    expect(names).toStrictEqual(['showLargePrintOnly', 'showNewArrivals'] satisfies SiblingBoolName[])
    expect(EMPTY_SIBLING_BOOLS).toStrictEqual({
      showNewArrivals: false,
      showLargePrintOnly: false,
    })
  })

  it('scope tag matches the phase-0 audit inventory', () => {
    const byName = Object.fromEntries(filterSchema.map((f) => [f.name, f.scope]))
    expect(byName).toStrictEqual({
      item_type: 'server',
      available_only: 'server',
      available_for_hold: 'server',
      year_min: 'server',
      year_max: 'server',
      location: 'server',
      publisher: 'server',
      reading_time: 'client-post',
      access: 'client-post',
      topic: 'client-post',
      language: 'server',
      min_lexile: 'server',
      max_lexile: 'server',
      subject_facets: 'server',
      author_facets: 'server',
      series_facets: 'server',
    } satisfies Record<FilterName, string>)
  })
})
