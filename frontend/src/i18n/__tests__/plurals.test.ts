/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeAll } from 'vitest'
import { loadLanguage, getTranslation } from '../translations'

// Regression: the ICU plural matcher only handled exact (=N) selectors and
// the 'other' keyword, so "{count, plural, one {# title} other {# titles}}"
// rendered "1 titles" for count=1.
describe('ICU plural categories', () => {
  beforeAll(async () => {
    await loadLanguage('en')
  })

  it('selects the "one" category for count=1', () => {
    expect(getTranslation('browseSeries.titleCount', 'en', { count: 1 })).toBe('1 title')
  })

  it('selects "other" for count=0 and count>1', () => {
    expect(getTranslation('browseSeries.titleCount', 'en', { count: 0 })).toBe('0 titles')
    expect(getTranslation('browseSeries.titleCount', 'en', { count: 5 })).toBe('5 titles')
  })

  it('still prefers exact matches over categories', () => {
    // catalog.resultsCount uses =0/=1 exact selectors plus 'other'
    expect(getTranslation('catalog.resultsCount', 'en', { count: 0 })).toBe('No items found')
    expect(getTranslation('catalog.resultsCount', 'en', { count: 1 })).toBe('1 item found')
    expect(getTranslation('catalog.resultsCount', 'en', { count: 3 })).toBe('3 items found')
  })
})
