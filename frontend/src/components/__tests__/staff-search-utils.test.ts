/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it } from 'vitest'
import { buildDidYouMean, fuzzyScore, rankStaffSearchResults, type StaffSearchResult } from '../header-search/staff-search-utils'

describe('staff-search-utils', () => {
  const sampleResults: StaffSearchResult[] = [
    {
      id: 'patron-1',
      type: 'patron',
      title: 'Maria Gonzalez',
      subtitle: 'P1234 • maria@example.com',
      route: '/staff/patrons',
      searchableText: 'maria gonzalez patron id p1234',
    },
    {
      id: 'item-1',
      type: 'item',
      title: 'The Library Book',
      subtitle: 'Susan Orlean • 9781476740188',
      route: '/catalog',
      searchableText: 'isbn 9781476740188 barcode 3123123',
    },
  ]

  it('supports fuzzy matches for small misspellings', () => {
    const score = fuzzyScore('mria gonzales', 'Maria Gonzalez')
    expect(score).toBeGreaterThan(0.6)
  })

  it('ranks likely matches first', () => {
    const ranked = rankStaffSearchResults('maria', sampleResults)
    expect(ranked[0]!.type).toBe('patron')
  })

  it('returns a did-you-mean suggestion when confidence is not exact', () => {
    const ranked = rankStaffSearchResults('gonzles', sampleResults)
    const suggestion = buildDidYouMean('gonzles', ranked)
    expect(suggestion).toBe('Maria Gonzalez')
  })
})
