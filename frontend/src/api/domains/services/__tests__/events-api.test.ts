/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { whenToRange } from '../events-api'

const DAY_MS = 24 * 60 * 60 * 1000

describe('whenToRange', () => {
  it('"today" spans the local calendar day surrounding now', () => {
    const now = new Date('2026-05-22T15:30:00')
    const { starts_after, starts_before } = whenToRange('today', now)
    const after = starts_after ?? ''
    const before = starts_before ?? ''
    expect(after).not.toBe('')
    expect(before).not.toBe('')
    expect(new Date(after).getTime()).toBeLessThanOrEqual(now.getTime())
    expect(new Date(before).getTime()).toBeGreaterThanOrEqual(now.getTime())
    // 00:00:00.000 -> 23:59:59.999
    expect(new Date(before).getTime() - new Date(after).getTime()).toBe(DAY_MS - 1)
  })

  it('"week" spans the next 7 days from now', () => {
    const now = new Date('2026-05-22T15:30:00')
    const { starts_after, starts_before } = whenToRange('week', now)
    expect(starts_after).toBe(now.toISOString())
    expect(new Date(starts_before ?? '').getTime() - now.getTime()).toBe(7 * DAY_MS)
  })

  it('"weekend" resolves to a Saturday -> Sunday span regardless of the weekday', () => {
    const wed = new Date('2026-05-20T12:00:00')
    const { starts_after, starts_before } = whenToRange('weekend', wed)
    expect(new Date(starts_after ?? '').getDay()).toBe(6) // Saturday
    expect(new Date(starts_before ?? '').getDay()).toBe(0) // Sunday
    expect(new Date(starts_after ?? '').getTime()).toBeGreaterThan(wed.getTime())
  })

  it('"weekend" on a Sunday still covers that same weekend', () => {
    // Walk forward to a guaranteed Sunday so the test is calendar-agnostic.
    const sun = new Date('2026-05-22T12:00:00')
    while (sun.getDay() !== 0) sun.setDate(sun.getDate() + 1)
    const { starts_after, starts_before } = whenToRange('weekend', sun)
    expect(new Date(starts_after ?? '').getDay()).toBe(6) // the preceding Saturday
    expect(new Date(starts_before ?? '').getDay()).toBe(0) // Sunday
    expect(new Date(starts_after ?? '').getTime()).toBeLessThanOrEqual(sun.getTime())
    expect(new Date(starts_before ?? '').getTime()).toBeGreaterThanOrEqual(sun.getTime())
  })
})
