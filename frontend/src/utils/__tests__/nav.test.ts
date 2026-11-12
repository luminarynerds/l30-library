/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { isActive } from '../nav'

describe('isActive', () => {
  it('returns true for exact match', () => {
    expect(isActive('/catalog', '/catalog')).toBe(true)
  })

  it('returns true for path-segment prefix', () => {
    expect(isActive('/catalog/123', '/catalog')).toBe(true)
  })

  it('does not substring-match', () => {
    // /staff should not match /staff-only-page
    expect(isActive('/staff-only-page', '/staff')).toBe(false)
  })

  it('respects exact option', () => {
    expect(isActive('/staff/circulation', '/staff', { exact: true })).toBe(false)
    expect(isActive('/staff', '/staff', { exact: true })).toBe(true)
  })

  it('uses knownPaths to defer to more-specific match', () => {
    // When both /staff and /staff/circulation are in known paths and we're on
    // /staff/circulation, only /staff/circulation should be active.
    const known = ['/staff', '/staff/circulation', '/staff/holds']
    expect(isActive('/staff/circulation', '/staff', { knownPaths: known })).toBe(false)
    expect(isActive('/staff/circulation', '/staff/circulation', { knownPaths: known })).toBe(true)
  })

  it('still returns true for less-specific match when no more-specific path matches', () => {
    const known = ['/staff', '/staff/holds']
    // /staff/unknown-subpage — only /staff matches.
    expect(isActive('/staff/unknown-subpage', '/staff', { knownPaths: known })).toBe(true)
  })

  it('returns false when paths diverge', () => {
    expect(isActive('/events', '/catalog')).toBe(false)
  })
})
