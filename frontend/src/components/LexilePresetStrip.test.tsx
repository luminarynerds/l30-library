/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { LexilePresetStrip } from './LexilePresetStrip'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      const map: Record<string, string> = {
        lexile_preset_title: 'Find a book at your reading level',
        lexile_preset_just_starting: 'Just starting',
        lexile_preset_early_reader: 'Early reader',
        lexile_preset_confident_reader: 'Confident reader',
        lexile_preset_strong_reader: 'Strong reader',
        lexile_preset_advanced: 'Advanced',
      }
      if (key === 'lexile_preset_aria' && params) {
        return `Find ${params.label} books, Lexile ${params.min} to ${params.max}`
      }
      return map[key] ?? key
    },
  }),
}))

const wrap = (n: React.ReactNode) => <MemoryRouter>{n}</MemoryRouter>

describe('LexilePresetStrip', () => {
  it('renders five kid bands with linked ranges', () => {
    render(wrap(<LexilePresetStrip />))
    expect(screen.getAllByRole('link')).toHaveLength(5)
    const early = screen.getByRole('link', { name: /Early reader/ })
    expect(early.getAttribute('href')).toContain('min_lexile=100')
    expect(early.getAttribute('href')).toContain('max_lexile=400')
  })

  it('renders four teen bands when TEEN_BANDS given', async () => {
    const { TEEN_BANDS } = await import('./LexilePresetStrip')
    render(wrap(<LexilePresetStrip bands={TEEN_BANDS} />))
    expect(screen.getAllByRole('link')).toHaveLength(4)
  })
})
