/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * Banned Books Week dates are set by the Banned Books Week Coalition. They
 * are NOT derivable from a calendar rule: the observance moved out of
 * September for 2026. A previous version of this module computed "the last
 * full Sun-Sat window inside September" and published a wrong date on the
 * public page.
 *
 * To add a year: take the dates and theme from bannedbooksweek.org and add
 * the entry to BOTH this table and
 * backend/app/seeds/fixtures/banned_books_week.json. A test asserts the two
 * agree. Never add a computed fallback; an absent date is correct, a
 * guessed one is not.
 */

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

export type BannedBooksWeekYear = {
  start: Date
  end: Date
  theme: string | null
  freedomReadDay: Date | null
}

// Local-midnight Dates so formatting does not drift across timezones.
const BANNED_BOOKS_WEEK: Record<number, BannedBooksWeekYear> = {
  2026: {
    start: new Date(2026, 9, 4),
    end: new Date(2026, 9, 10),
    theme: 'Let Books Be. Protect the Freedom to Read.',
    freedomReadDay: new Date(2026, 9, 10),
  },
  // Dates announced at https://www.ala.org/bbooks/banned (checked 2026-10-12).
  // The 2027 theme and Let Freedom Read Day have not been announced there.
  2027: {
    start: new Date(2027, 9, 3),
    end: new Date(2027, 9, 9),
    theme: null,
    freedomReadDay: null,
  },
}

export const KNOWN_YEARS: number[] = Object.keys(BANNED_BOOKS_WEEK)
  .map(Number)
  .sort((a, b) => a - b)

export function bannedBooksWeekFor(year: number): BannedBooksWeekYear | null {
  return BANNED_BOOKS_WEEK[year] ?? null
}

export function formatBannedBooksWeek(window: { start: Date; end: Date }): string {
  const startMonth = MONTH_NAMES[window.start.getMonth()]
  const endMonth = MONTH_NAMES[window.end.getMonth()]
  const year = window.start.getFullYear()
  if (startMonth === endMonth) {
    return `${startMonth} ${window.start.getDate()}-${window.end.getDate()}, ${year}`
  }
  return `${startMonth} ${window.start.getDate()} - ${endMonth} ${window.end.getDate()}, ${year}`
}

/**
 * The soonest known window that has not finished yet, or null when the
 * table has run out. Null is a valid, expected state: the caller renders
 * the section without a date rather than inventing one.
 */
export function nextBannedBooksWeek(
  now: Date = new Date()
): (BannedBooksWeekYear & { formatted: string }) | null {
  const cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const upcoming = KNOWN_YEARS
    .map(year => BANNED_BOOKS_WEEK[year])
    .filter((window): window is BannedBooksWeekYear => window !== undefined)
    .filter(window => window.end.getTime() >= cutoff)
    .sort((a, b) => a.start.getTime() - b.start.getTime())

  const target = upcoming[0]
  return target ? { ...target, formatted: formatBannedBooksWeek(target) } : null
}
