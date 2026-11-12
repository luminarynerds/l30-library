/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TodayStrip from './TodayStrip'

vi.mock('@tanstack/react-query', () => ({ useQuery: () => ({ data: { stations: [] } }) }))
vi.mock('@/i18n/I18nContext', () => ({ useTranslation: () => ({ t: (key: string, fallback?: string) => fallback ?? key }) }))

describe('TodayStrip service claims', () => {
  it('does not advertise unconfigured tech help just because the library is open', () => {
    render(<MemoryRouter><TodayStrip openStatus={{ is_open: true, closes_at: '20:00', opens_at: '09:00', reason: null }} events={[]} todayHoursLabel={null} /></MemoryRouter>)
    expect(screen.getByText('Come on in')).toBeInTheDocument()
    expect(screen.queryByText(/walk-in tech help/i)).not.toBeInTheDocument()
  })
})
