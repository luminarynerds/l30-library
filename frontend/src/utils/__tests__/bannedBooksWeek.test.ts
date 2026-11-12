/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import {
  KNOWN_YEARS,
  bannedBooksWeekFor,
  formatBannedBooksWeek,
  nextBannedBooksWeek,
} from '../bannedBooksWeek'

const HERE = dirname(fileURLToPath(import.meta.url))
const FIXTURE = resolve(
  HERE,
  '../../../../backend/app/seeds/fixtures/banned_books_week.json'
)

describe('bannedBooksWeekFor', () => {
  it('returns the Coalition dates for 2026, which are in October', () => {
    const w = bannedBooksWeekFor(2026)
    expect(w).not.toBeNull()
    expect(w!.start.getFullYear()).toBe(2026)
    expect(w!.start.getMonth()).toBe(9) // October, 0-indexed
    expect(w!.start.getDate()).toBe(4)
    expect(w!.end.getMonth()).toBe(9)
    expect(w!.end.getDate()).toBe(10)
    expect(w!.theme).toBe('Let Books Be. Protect the Freedom to Read.')
    expect(w!.freedomReadDay?.getDate()).toBe(10)
  })

  it('keeps the announced 2027 dates without inventing its theme or action day', () => {
    const w = bannedBooksWeekFor(2027)
    expect(w).not.toBeNull()
    expect(formatBannedBooksWeek(w!)).toBe('October 3-9, 2027')
    expect(w!.theme).toBeNull()
    expect(w!.freedomReadDay).toBeNull()
  })

  it('returns null for a year that is not in the table', () => {
    expect(bannedBooksWeekFor(2031)).toBeNull()
  })

  it('never derives a date from a calendar rule', () => {
    // 2025 is deliberately absent. A derivation would have produced a
    // September window here; the whole defect this module fixes.
    expect(bannedBooksWeekFor(2025)).toBeNull()
  })
})

describe('formatBannedBooksWeek', () => {
  it('formats a same-month window', () => {
    expect(
      formatBannedBooksWeek({
        start: new Date(2026, 9, 4),
        end: new Date(2026, 9, 10),
      })
    ).toBe('October 4-10, 2026')
  })

  it('formats a window that straddles two months', () => {
    expect(
      formatBannedBooksWeek({
        start: new Date(2027, 8, 26),
        end: new Date(2027, 9, 2),
      })
    ).toBe('September 26 - October 2, 2027')
  })
})

describe('nextBannedBooksWeek', () => {
  it('returns the 2026 window well before it starts', () => {
    const r = nextBannedBooksWeek(new Date(2026, 0, 15))
    expect(r!.formatted).toBe('October 4-10, 2026')
  })

  it('still returns the current window during the week itself', () => {
    const r = nextBannedBooksWeek(new Date(2026, 9, 7))
    expect(r!.formatted).toBe('October 4-10, 2026')
  })

  it('still returns the window on its final day', () => {
    const r = nextBannedBooksWeek(new Date(2026, 9, 10))
    expect(r!.formatted).toBe('October 4-10, 2026')
  })

  it('returns null once every known window has passed', () => {
    expect(nextBannedBooksWeek(new Date(2027, 9, 10))).toBeNull()
  })

  it('moves to the announced 2027 window after the 2026 observance ends', () => {
    const r = nextBannedBooksWeek(new Date(2026, 9, 12))
    expect(r?.formatted).toBe('October 3-9, 2027')
    expect(r?.theme).toBeNull()
    expect(r?.freedomReadDay).toBeNull()
  })
})

describe('rollover alarm', () => {
  // Deliberate: this test goes red when the table runs out. That is the
  // alarm. If you are reading this because CI is red, the fix is to add
  // next year's entry from bannedbooksweek.org to BOTH
  // frontend/src/utils/bannedBooksWeek.ts and
  // backend/app/seeds/fixtures/banned_books_week.json. Do not delete or
  // relax this test, and do not add a computed fallback.
  it('has an entry that has not yet ended', () => {
    const newest = Math.max(...KNOWN_YEARS)
    const w = bannedBooksWeekFor(newest)!
    expect(w.end.getTime()).toBeGreaterThanOrEqual(Date.now())
  })
})

describe('fixture drift', () => {
  it('matches the backend seed fixture exactly', () => {
    const fixture = JSON.parse(readFileSync(FIXTURE, 'utf8')) as Record<
      string,
      { start: string; end: string; theme: string | null; freedom_read_day: string | null }
    >
    const iso = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
        d.getDate()
      ).padStart(2, '0')}`

    expect(Object.keys(fixture).map(Number).sort()).toEqual([...KNOWN_YEARS].sort())
    for (const year of KNOWN_YEARS) {
      const ts = bannedBooksWeekFor(year)!
      const fx = fixture[String(year)]!
      expect(iso(ts.start)).toBe(fx.start)
      expect(iso(ts.end)).toBe(fx.end)
      expect(ts.theme).toBe(fx.theme)
      expect(ts.freedomReadDay ? iso(ts.freedomReadDay) : null).toBe(fx.freedom_read_day)
    }
  })
})
