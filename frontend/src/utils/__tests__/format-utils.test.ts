/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it } from 'vitest'

import { formatCurrency, formatDate, formatDateTime, formatEnumLabel, formatStatus, parseDate } from '../format-utils'

describe('format-utils', () => {
  describe('formatStatus', () => {
    it('converts snake_case to title case', () => {
      expect(formatStatus('written_off')).toBe('Written Off')
    })
  })

  describe('parseDate', () => {
    it('returns null for missing values', () => {
      expect(parseDate(null)).toBeNull()
      expect(parseDate(undefined)).toBeNull()
      expect(parseDate('')).toBeNull()
    })

    it('returns null for unparseable strings', () => {
      expect(parseDate('not-a-date')).toBeNull()
      expect(parseDate('abc123')).toBeNull()
    })

    it('parses bare YYYY-MM-DD as local midnight (no UTC shift)', () => {
      // Regression test for the timezone bug: `new Date("2025-09-01")` is
      // parsed as UTC midnight, which renders as 2025-08-31 in any timezone
      // west of UTC. parseDate should keep the same calendar day everywhere.
      const parsed = parseDate('2025-09-01')
      expect(parsed).not.toBeNull()
      expect(parsed!.getFullYear()).toBe(2025)
      expect(parsed!.getMonth()).toBe(8) // September (0-indexed)
      expect(parsed!.getDate()).toBe(1)
      expect(parsed!.getHours()).toBe(0)
    })

    it('parses full ISO timestamps using existing semantics', () => {
      const parsed = parseDate('2025-03-15T14:30:00Z')
      expect(parsed).not.toBeNull()
      expect(parsed!.toISOString()).toBe('2025-03-15T14:30:00.000Z')
    })

    it('passes through valid Date objects', () => {
      const d = new Date('2025-03-15T14:30:00Z')
      expect(parseDate(d)).toBe(d)
    })

    it('returns null for invalid Date objects', () => {
      expect(parseDate(new Date('not-a-date'))).toBeNull()
    })
  })

  describe('formatDate', () => {
    it('returns fallback for missing values', () => {
      expect(formatDate(null)).toBe('-')
      expect(formatDate(undefined)).toBe('-')
    })

    it('returns fallback for invalid date strings', () => {
      expect(formatDate('not-a-date')).toBe('-')
      expect(formatDate('')).toBe('-')
      expect(formatDate('2025-13-45')).toBe('-')
      expect(formatDate('abc123')).toBe('-')
    })

    it('formats valid ISO date strings correctly', () => {
      const result = formatDate('2025-03-15T12:00:00Z')
      // Result should contain month, day, year - exact format varies by locale
      expect(result).toMatch(/Mar.*15.*2025/)
    })

    it('formats valid date strings without time', () => {
      const result = formatDate('2025-06-01')
      expect(result).toMatch(/Jun.*1.*2025/)
    })
  })

  describe('formatDateTime', () => {
    it('returns fallback for missing values', () => {
      expect(formatDateTime(null)).toBe('-')
      expect(formatDateTime(undefined)).toBe('-')
    })

    it('returns fallback for invalid date strings', () => {
      expect(formatDateTime('not-a-date')).toBe('-')
      expect(formatDateTime('')).toBe('-')
      expect(formatDateTime('2025-13-45')).toBe('-')
      expect(formatDateTime('abc123')).toBe('-')
    })

    it('formats valid ISO datetime strings correctly', () => {
      const result = formatDateTime('2025-03-15T14:30:00Z')
      // Result should contain month, day, year, and a time with :30. The
      // hour will render in 12-hour US locale (e.g. "2:30 PM" in UTC), and
      // can shift in non-UTC test environments — so only assert minute.
      expect(result).toMatch(/Mar.*15.*2025/)
      expect(result).toMatch(/:30/)
    })

    it('formats valid date strings without time', () => {
      const result = formatDateTime('2025-06-01')
      expect(result).toMatch(/Jun.*1.*2025/)
    })
  })

  describe('formatCurrency', () => {
    it('formats numbers as USD currency string', () => {
      expect(formatCurrency(12.5)).toBe('$12.50')
    })

    it('returns fallback for nullish amount', () => {
      expect(formatCurrency(null)).toBe('-')
      expect(formatCurrency(undefined)).toBe('-')
    })
  })

  describe('formatEnumLabel', () => {
    it('passes through canonical lowercase enum values unchanged', () => {
      expect(formatEnumLabel('political_viewpoint')).toBe('political_viewpoint')
    })

    it('strips ClassName. prefix and lowercases when a Python enum repr leaks through', () => {
      expect(formatEnumLabel('ChallengeReason.POLITICAL_VIEWPOINT')).toBe('political_viewpoint')
      expect(formatEnumLabel('ChallengeOutcome.RETAINED')).toBe('retained')
    })

    it('returns empty string for null', () => {
      expect(formatEnumLabel(null)).toBe('')
    })

    it('returns empty string for undefined', () => {
      expect(formatEnumLabel(undefined)).toBe('')
    })
  })
})
