/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { getNavConfig } from '../navConfig'

const t = (k: string, fallback?: string) => fallback ?? k

function configWith(overrides: Record<string, boolean> = {}, isAuthenticated = false) {
  const flags: Record<string, boolean> = {
    front_desk_enabled: true,
    home_delivery_enabled: true,
    meeting_rooms_enabled: true,
    tech_services_enabled: true,
    legal_services_enabled: true,
    board_features_enabled: true,
    makerspace_enabled: true,
    community_features_enabled: true,
    book_clubs_enabled: true,
    collection_management_enabled: true,
    reading_programs_enabled: true,
    ai_tools_enabled: true,
    banned_books_tracking_enabled: true,
    learning_platform_enabled: true,
    indie_platform_enabled: true,
    for_teachers_enabled: true,
    ...overrides,
  }
  return getNavConfig({
    t,
    isFeatureEnabled: (f: string) => flags[f] ?? false,
    isAuthenticated,
    role: null,
  })
}

describe('getNavConfig', () => {
  it('returns Services and Explore by default; Teachers only when authed + flagged', () => {
    const anon = configWith()
    expect(anon.map(g => g.key)).toEqual(['services', 'explore'])

    const authed = configWith({}, true)
    expect(authed.map(g => g.key)).toEqual(['services', 'explore', 'teachers'])
  })

  it('omits a section when every item is flag-gated off', () => {
    // read-and-discover always keeps /picks, /coming-soon, and
    // /catalog/partner-search unconditionally, so it can never fully empty.
    // learn-and-create is entirely flag-gated and can.
    const groups = configWith({
      ai_tools_enabled: false,
      banned_books_tracking_enabled: false,
      learning_platform_enabled: false,
      indie_platform_enabled: false,
    })
    const explore = groups.find(g => g.key === 'explore')
    expect(explore).toBeDefined()
    expect(explore!.sections.find(s => s.key === 'learn-and-create')).toBeUndefined()
  })

  it('keeps the Explore group (via always-on discovery items) even when every gated item is off', () => {
    const groups = configWith({
      community_features_enabled: false,
      book_clubs_enabled: false,
      collection_management_enabled: false,
      reading_programs_enabled: false,
      ai_tools_enabled: false,
      banned_books_tracking_enabled: false,
      learning_platform_enabled: false,
      indie_platform_enabled: false,
    })
    const explore = groups.find(g => g.key === 'explore')
    expect(explore).toBeDefined()
    expect(explore!.sections.map(s => s.key)).toEqual(['read-and-discover'])
    const items = explore!.sections.flatMap(s => s.items)
    expect(items.map(i => i.to)).toEqual(['/picks', '/coming-soon', '/catalog/partner-search'])
  })

  it('omits Teachers when feature flag is off even if authenticated', () => {
    const groups = configWith({ for_teachers_enabled: false }, true)
    expect(groups.find(g => g.key === 'teachers')).toBeUndefined()
  })

  it('includes a Coming Soon item under Explore', () => {
    const groups = configWith()
    const explore = groups.find(g => g.key === 'explore')
    const allItems = explore!.sections.flatMap(s => s.items)
    expect(allItems.some(i => i.to === '/coming-soon')).toBe(true)
  })
})
