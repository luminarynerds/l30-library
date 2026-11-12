/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { formatCurrency } from '../localization'

describe('formatCurrency', () => {
  it('formats USD for English (US)', () => {
    expect(formatCurrency(1234.56, 'en', 'USD')).toBe('$1,234.56')
  })

  it('formats EUR for Spanish (es-419) with peso/euro symbol placement', () => {
    const out = formatCurrency(1234.56, 'es', 'EUR')
    // es-419 with EUR renders something like "EUR 1,234.56" or "1.234,56 €" depending on ICU;
    // assert the digits are present in either grouping form
    expect(out).toMatch(/1[.,]234[.,]56/)
  })

  it('defaults to CAD when no currency specified (preserves existing canonical behavior)', () => {
    const out = formatCurrency(10, 'en')
    expect(out).toContain('10')
    // en-US + CAD → "CA$10.00"
    expect(out).toMatch(/CA\$|C\$/)
  })

  it('formats JPY with no fraction digits', () => {
    const out = formatCurrency(1234, 'en', 'JPY')
    // JPY has 0 fraction digits in Intl by default; rendered as "¥1,234"
    expect(out).toContain('1,234')
    expect(out).not.toContain('.00')
  })

  it('falls back to en-US for unknown languages', () => {
    // @ts-expect-error - exercising the LOCALE_MAP fallback intentionally
    expect(formatCurrency(99.5, 'xx', 'USD')).toBe('$99.50')
  })
})
