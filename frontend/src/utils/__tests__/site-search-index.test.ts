/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it } from 'vitest'
import { searchStaticSiteIndex } from '../site-search-index'

describe('searchStaticSiteIndex', () => {
  it('returns matching public pages for a keyword', () => {
    const results = searchStaticSiteIndex('makerspace')
    expect(results.length).toBeGreaterThan(0)
    expect(results[0]?.url).toBe('/makerspace')
  })

  it('returns an empty array for empty query', () => {
    expect(searchStaticSiteIndex('   ')).toEqual([])
  })
})
