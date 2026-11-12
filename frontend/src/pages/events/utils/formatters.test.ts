/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it } from 'vitest'

import {
  LIBRARY_TIMEZONE,
  formatDurationMinutes,
  formatEventDateTimeRange,
  formatFullDate,
  formatTime,
} from './formatters'

describe('formatters / formatTime', () => {
  it('renders in library tz, not the runner browser tz', () => {
    // 08:14:09 UTC -> 04:14 ET (winter) / 04:14 EDT (summer DST). May = EDT.
    // Either way the value MUST NOT come out as "8:14 AM" (UTC) or "2:14 AM" (MDT).
    expect(formatTime('2026-05-28T08:14:09.151466Z')).toBe('4:14 AM')
  })

  it('drops seconds and sub-second cruft', () => {
    const out = formatTime('2026-06-08T11:44:09.151466Z')
    expect(out).not.toMatch(/:\d{2}:\d{2}/) // no HH:MM:SS
    expect(out).not.toContain('.151')
    expect(out).not.toContain('Z')
  })

  it('formats a clean UTC hour at expected ET wall time', () => {
    // 17:00 UTC = 1:00 PM EDT (May is DST).
    expect(formatTime('2026-05-22T17:00:00Z')).toBe('1:00 PM')
  })
})

describe('formatters / formatFullDate', () => {
  it('uses library tz so midnight-Z values do not roll back a day', () => {
    // 2026-05-23T03:00:00Z = 2026-05-22 11:00 PM EDT. Day MUST be Friday May 22.
    expect(formatFullDate('2026-05-23T03:00:00Z')).toBe('Friday, May 22, 2026')
  })
})

describe('formatters / formatDurationMinutes', () => {
  it('renders minutes-only under 60', () => {
    expect(formatDurationMinutes(30)).toBe('30 min')
    expect(formatDurationMinutes(45)).toBe('45 min')
  })

  it('renders round hours', () => {
    expect(formatDurationMinutes(60)).toBe('1 hr')
    expect(formatDurationMinutes(120)).toBe('2 hrs')
  })

  it('renders hr + min', () => {
    expect(formatDurationMinutes(90)).toBe('1 hr 30 min')
    expect(formatDurationMinutes(150)).toBe('2 hrs 30 min')
  })

  it('returns empty for zero/negative/non-finite', () => {
    expect(formatDurationMinutes(0)).toBe('')
    expect(formatDurationMinutes(-15)).toBe('')
    expect(formatDurationMinutes(Number.NaN)).toBe('')
  })
})

describe('formatters / formatEventDateTimeRange', () => {
  it('returns day + start time when no end provided', () => {
    // 17:00 UTC = 1:00 PM EDT, Friday May 22.
    expect(formatEventDateTimeRange('2026-05-22T17:00:00Z')).toBe('Fri, 1:00 PM')
  })

  it('appends duration for a 30-minute event', () => {
    expect(
      formatEventDateTimeRange('2026-05-22T17:00:00Z', '2026-05-22T17:30:00Z'),
    ).toBe('Fri, 1:00 PM (30 min)')
  })

  it('appends duration for a 90-minute event', () => {
    expect(
      formatEventDateTimeRange('2026-05-22T17:00:00Z', '2026-05-22T18:30:00Z'),
    ).toBe('Fri, 1:00 PM (1 hr 30 min)')
  })

  it('renders an all-day event when start is library-midnight and span >= 23h', () => {
    // 2026-05-22 04:00:00Z = 2026-05-22 00:00 EDT (midnight ET).
    // End 24h later still same calendar day in ET? End = 2026-05-23 04:00Z = 2026-05-23 00:00 EDT.
    // Different ET day -> falls into multi-day branch. Build a single-day all-day instead:
    // start 2026-05-22 04:00Z (Fri 00:00 ET), end 2026-05-23 03:59Z (Fri 23:59 ET).
    expect(
      formatEventDateTimeRange('2026-05-22T04:00:00Z', '2026-05-23T03:59:00Z'),
    ).toBe('Fri, May 22 (all-day)')
  })

  it('renders multi-day ranges with short dates on both ends', () => {
    // Fri May 22 -> Sun May 24 (in ET).
    expect(
      formatEventDateTimeRange('2026-05-22T14:00:00Z', '2026-05-24T20:00:00Z'),
    ).toBe('Fri, May 22 - Sun, May 24')
  })

  it('honors includeDate option for richer single-day labels', () => {
    expect(
      formatEventDateTimeRange(
        '2026-05-22T17:00:00Z',
        '2026-05-22T18:30:00Z',
        { includeDate: true },
      ),
    ).toBe('Fri, May 22, 1:00 PM (1 hr 30 min)')
  })

  it('tolerates invalid end and falls back to start-only', () => {
    expect(
      formatEventDateTimeRange('2026-05-22T17:00:00Z', 'not-a-date'),
    ).toBe('Fri, 1:00 PM')
  })

  it('returns empty string for invalid start', () => {
    expect(formatEventDateTimeRange('garbage')).toBe('')
  })
})

describe('formatters / LIBRARY_TIMEZONE export', () => {
  it('is the canonical Eastern zone', () => {
    expect(LIBRARY_TIMEZONE).toBe('America/New_York')
  })
})
