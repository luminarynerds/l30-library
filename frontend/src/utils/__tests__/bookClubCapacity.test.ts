/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeAll } from 'vitest'
import { loadLanguage } from '@/i18n/translations'
import {
  patronCapacityBadge,
  staffCapacityTone,
} from '../bookClubCapacity'

beforeAll(async () => {
  await loadLanguage('en')
})

describe('patronCapacityBadge', () => {
  it('returns null when the club is uncapped (max_members null)', () => {
    expect(
      patronCapacityBadge(
        { currentMemberCount: 4, maxMembers: null, waitlistCount: 0, isFull: false },
        true,
      ),
    ).toBeNull()
  })

  it('shows N/Max members when capped and not full', () => {
    expect(
      patronCapacityBadge(
        { currentMemberCount: 7, maxMembers: 12, waitlistCount: 0, isFull: false },
        true,
      ),
    ).toBe('7/12 members')
  })

  it('shows plain Full when full but waitlist flag is OFF', () => {
    expect(
      patronCapacityBadge(
        { currentMemberCount: 12, maxMembers: 12, waitlistCount: 3, isFull: true },
        false,
      ),
    ).toBe('Full')
  })

  it('shows Full + waiting count when full and flag ON and >0 waiting', () => {
    expect(
      patronCapacityBadge(
        { currentMemberCount: 12, maxMembers: 12, waitlistCount: 3, isFull: true },
        true,
      ),
    ).toBe('Full · 3 waiting')
  })

  it('shows plain Full when full, flag ON, but 0 waiting', () => {
    expect(
      patronCapacityBadge(
        { currentMemberCount: 12, maxMembers: 12, waitlistCount: 0, isFull: true },
        true,
      ),
    ).toBe('Full')
  })
})

describe('staffCapacityTone', () => {
  it('none when uncapped', () => {
    expect(staffCapacityTone(5, null)).toBe('none')
    expect(staffCapacityTone(5, undefined)).toBe('none')
    expect(staffCapacityTone(5, 0)).toBe('none')
  })

  it('full at or over capacity', () => {
    expect(staffCapacityTone(12, 12)).toBe('full')
    expect(staffCapacityTone(13, 12)).toBe('full')
  })

  it('warn at >= 80% but below capacity', () => {
    expect(staffCapacityTone(10, 12)).toBe('warn') // 0.833
    expect(staffCapacityTone(8, 10)).toBe('warn') // exactly 0.8
  })

  it('normal below 80%', () => {
    expect(staffCapacityTone(7, 12)).toBe('normal') // 0.583
    expect(staffCapacityTone(0, 5)).toBe('normal')
  })
})
