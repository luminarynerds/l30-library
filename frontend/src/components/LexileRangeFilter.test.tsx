/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LexileRangeFilter, READING_LEVEL_BANDS } from './LexileRangeFilter'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => {
      const map: Record<string, string> = {
        lexile_filter_title: 'Reading level (Lexile)',
        lexile_filter_min: 'Minimum',
        lexile_filter_max: 'Maximum',
        lexile_filter_clear: 'Clear',
        lexile_filter_aria_min: 'Minimum Lexile, between -400 and 2000',
        lexile_filter_aria_max: 'Maximum Lexile, between -400 and 2000',
        'catalog.readingLevel.earlyReader': 'Early reader',
        'catalog.readingLevel.middleGrade': 'Middle grade',
        'catalog.readingLevel.teen': 'Teen',
        'catalog.readingLevel.adult': 'Adult',
        'catalog.readingLevel.groupLabel': 'Reading level presets',
        'catalog.readingLevel.ariaSuffix': 'Lexile {{min}} to {{max}}',
      }
      const v = map[key]
      if (v == null) {
        if (typeof paramsOrFallback === 'string') return paramsOrFallback
        return key
      }
      if (paramsOrFallback && typeof paramsOrFallback === 'object') {
        return Object.entries(paramsOrFallback).reduce(
          (acc, [k, val]) => acc.replace(`{{${k}}}`, String(val)),
          v,
        )
      }
      return v
    },
  }),
}))

describe('LexileRangeFilter', () => {
  it('calls onChange when min changes', () => {
    const onChange = vi.fn()
    render(<LexileRangeFilter min={null} max={null} onChange={onChange} />)
    fireEvent.change(screen.getByLabelText(/Minimum Lexile/i), { target: { value: '400' } })
    expect(onChange).toHaveBeenCalledWith({ min: 400, max: null })
  })

  it('clamps above 2000', () => {
    const onChange = vi.fn()
    render(<LexileRangeFilter min={null} max={null} onChange={onChange} />)
    fireEvent.change(screen.getByLabelText(/Maximum Lexile/i), { target: { value: '5000' } })
    expect(onChange).toHaveBeenCalledWith({ min: null, max: 2000 })
  })

  it('clear button resets', () => {
    const onChange = vi.fn()
    render(<LexileRangeFilter min={300} max={800} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: /clear/i }))
    expect(onChange).toHaveBeenCalledWith({ min: null, max: null })
  })

  describe('reading-level preset chips', () => {
    it('renders four preset chips', () => {
      render(<LexileRangeFilter min={null} max={null} onChange={vi.fn()} />)
      expect(screen.getByRole('button', { name: /Early reader/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Middle grade/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Teen/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Adult/i })).toBeInTheDocument()
    })

    it('exports band table with expected cutoffs', () => {
      const byKey = Object.fromEntries(
        READING_LEVEL_BANDS.map((b) => [b.key, { min: b.min, max: b.max }]),
      )
      expect(byKey['catalog.readingLevel.earlyReader']).toEqual({ min: 0, max: 500 })
      expect(byKey['catalog.readingLevel.middleGrade']).toEqual({ min: 500, max: 850 })
      expect(byKey['catalog.readingLevel.teen']).toEqual({ min: 850, max: 1100 })
      expect(byKey['catalog.readingLevel.adult']).toEqual({ min: 1100, max: 1500 })
    })

    it('clicking middle grade chip emits Lexile 500-850', () => {
      const onChange = vi.fn()
      render(<LexileRangeFilter min={null} max={null} onChange={onChange} />)
      fireEvent.click(screen.getByRole('button', { name: /Middle grade/i }))
      expect(onChange).toHaveBeenCalledWith({ min: 500, max: 850 })
    })

    it('chip whose range matches props is aria-pressed=true; others false', () => {
      render(<LexileRangeFilter min={500} max={850} onChange={vi.fn()} />)
      expect(screen.getByRole('button', { name: /Middle grade/i })).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByRole('button', { name: /Early reader/i })).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByRole('button', { name: /Teen/i })).toHaveAttribute('aria-pressed', 'false')
      expect(screen.getByRole('button', { name: /Adult/i })).toHaveAttribute('aria-pressed', 'false')
    })

    it('clicking the active chip clears the band', () => {
      const onChange = vi.fn()
      render(<LexileRangeFilter min={500} max={850} onChange={onChange} />)
      fireEvent.click(screen.getByRole('button', { name: /Middle grade/i }))
      expect(onChange).toHaveBeenCalledWith({ min: null, max: null })
    })

    it('out-of-band range leaves all chips unpressed', () => {
      render(<LexileRangeFilter min={600} max={700} onChange={vi.fn()} />)
      for (const key of READING_LEVEL_BANDS.map((b) => b.key)) {
        const label = key.split('.').pop()!
        const name = new RegExp(label.replace(/([A-Z])/g, ' $1'), 'i')
        expect(screen.getByRole('button', { name })).toHaveAttribute('aria-pressed', 'false')
      }
    })

    it('chip group has role=group with aria-label', () => {
      render(<LexileRangeFilter min={null} max={null} onChange={vi.fn()} />)
      expect(screen.getByRole('group', { name: /Reading level presets/i })).toBeInTheDocument()
    })
  })
})
