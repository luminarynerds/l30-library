/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { deriveBusyness } from '@/components/home/PlanYourVisit'

const open = { is_open: true, opens_at: null, closes_at: null, reason: null }
const closed = { is_open: false, opens_at: '09:00', closes_at: null, reason: null }

describe('deriveBusyness', () => {
  it('returns closed when library is not open', () => {
    expect(deriveBusyness(closed, 10, 10)).toBe('closed')
  })

  it('returns unknown when no lab data', () => {
    expect(deriveBusyness(open, null, null)).toBe('unknown')
  })

  it('returns unknown when total is 0', () => {
    expect(deriveBusyness(open, 0, 0)).toBe('unknown')
  })

  it('returns open_quiet when >=60% free (exactly 60%)', () => {
    expect(deriveBusyness(open, 6, 10)).toBe('open_quiet')
  })

  it('returns open_quiet when 100% free', () => {
    expect(deriveBusyness(open, 10, 10)).toBe('open_quiet')
  })

  it('returns open_moderate between 26% and 59% free', () => {
    expect(deriveBusyness(open, 5, 10)).toBe('open_moderate')
  })

  it('returns open_busy when <=25% free (exactly 25%)', () => {
    expect(deriveBusyness(open, 2, 8)).toBe('open_busy')
  })

  it('returns open_busy when 0 free', () => {
    expect(deriveBusyness(open, 0, 10)).toBe('open_busy')
  })

  it('returns closed for null openStatus', () => {
    expect(deriveBusyness(null, 10, 10)).toBe('closed')
  })
})
