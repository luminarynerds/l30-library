/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it } from 'vitest'
import {
  readFiltersFromStorage,
  readSiblingBoolsFromStorage,
  writeFiltersToStorage,
  writeSiblingBoolsToStorage,
} from '../storage'
import { EMPTY_FILTERS, EMPTY_SIBLING_BOOLS } from '../types'

describe('readFiltersFromStorage', () => {
  it('returns EMPTY_FILTERS for non-object input', () => {
    expect(readFiltersFromStorage(null)).toEqual(EMPTY_FILTERS)
    expect(readFiltersFromStorage(undefined)).toEqual(EMPTY_FILTERS)
    expect(readFiltersFromStorage('string')).toEqual(EMPTY_FILTERS)
    expect(readFiltersFromStorage(42)).toEqual(EMPTY_FILTERS)
  })

  it('reads valid fields and defaults the rest', () => {
    expect(readFiltersFromStorage({
      item_type: 'ebook',
      available_only: true,
      year_min: '2010',
      min_lexile: 500,
    })).toEqual({
      ...EMPTY_FILTERS,
      item_type: 'ebook',
      available_only: true,
      year_min: '2010',
      min_lexile: 500,
    })
  })

  it('drops fields whose runtime type does not match the schema declaration', () => {
    expect(readFiltersFromStorage({
      item_type: 42,                  // expected string-nullable
      available_only: { weird: true }, // expected boolean
      year_min: null,                 // expected string
      min_lexile: 'low',              // expected number-nullable
      max_lexile: NaN,                // not finite
    })).toEqual(EMPTY_FILTERS)
  })

  it('applies per-field maxLength caps', () => {
    const longLocation = 'x'.repeat(200)
    const longPublisher = 'y'.repeat(200)
    const longLanguage = 'eng-US-extended'
    const out = readFiltersFromStorage({
      location: longLocation,
      publisher: longPublisher,
      language: longLanguage,
    })
    expect(out.location).toHaveLength(50)
    expect(out.publisher).toHaveLength(100)
    expect(out.language).toHaveLength(10)
  })

  it('migrates legacy topic value `ya` to `young_adult`', () => {
    expect(readFiltersFromStorage({ topic: 'ya' }).topic).toBe('young_adult')
    expect(readFiltersFromStorage({ topic: 'young_adult' }).topic).toBe('young_adult')
    expect(readFiltersFromStorage({ topic: 'fiction' }).topic).toBe('fiction')
  })

  it('drops topic when value is not a string', () => {
    expect(readFiltersFromStorage({ topic: 7 }).topic).toBe('')
  })
})

describe('readSiblingBoolsFromStorage', () => {
  it('reads valid booleans', () => {
    expect(readSiblingBoolsFromStorage({
      showNewArrivals: true,
      showLargePrintOnly: true,
    })).toEqual({ showNewArrivals: true, showLargePrintOnly: true })
  })

  it('defaults missing or wrong-typed bools to false', () => {
    expect(readSiblingBoolsFromStorage({})).toEqual(EMPTY_SIBLING_BOOLS)
    expect(readSiblingBoolsFromStorage({
      showNewArrivals: 'true',
      showLargePrintOnly: 1,
    })).toEqual(EMPTY_SIBLING_BOOLS)
  })

  it('returns defaults for non-object input', () => {
    expect(readSiblingBoolsFromStorage(null)).toEqual(EMPTY_SIBLING_BOOLS)
    expect(readSiblingBoolsFromStorage(42)).toEqual(EMPTY_SIBLING_BOOLS)
  })
})

describe('round-trip', () => {
  it('read(write(x)) preserves filters', () => {
    const original = {
      ...EMPTY_FILTERS,
      item_type: 'ebook',
      available_only: true,
      year_min: '2010',
      year_max: '2020',
      location: 'Adult Fiction',
      publisher: 'Penguin',
      reading_time: 'short',
      access: 'audio',
      topic: 'young_adult',
      language: 'eng',
      min_lexile: 500,
      max_lexile: 1200,
    }
    expect(readFiltersFromStorage(writeFiltersToStorage(original))).toEqual(original)
  })

  it('read(write(x)) preserves sibling bools', () => {
    const original = { showNewArrivals: true, showLargePrintOnly: true }
    expect(readSiblingBoolsFromStorage(writeSiblingBoolsToStorage(original))).toEqual(original)
  })
})
