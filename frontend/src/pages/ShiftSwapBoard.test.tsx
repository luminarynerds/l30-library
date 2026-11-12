/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}))

vi.mock('../styles/shift-swap-board.css', () => ({}))

vi.mock('../api/shift-swap-api', () => ({
  shiftSwapApi: {
    getListings: vi.fn().mockResolvedValue({ listings: [] }),
    getNotifications: vi.fn().mockResolvedValue({ notifications: [] }),
    getMatches: vi.fn().mockResolvedValue({ matches: [] }),
  },
}))

vi.mock('../components/shift-swap/ShiftSwapBoardView', () => ({ default: () => <div /> }))
vi.mock('../components/shift-swap/CreateListingModal', () => ({ default: () => <div /> }))
vi.mock('../components/shift-swap/ListingDetailsModal', () => ({ default: () => <div /> }))
vi.mock('../components/shift-swap/ShiftSwapNotifications', () => ({ default: () => <div /> }))
vi.mock('../components/shift-swap/PreferencesPanel', () => ({ default: () => <div /> }))
vi.mock('../components/shift-swap/ReliabilityScore', () => ({ default: () => <div /> }))
vi.mock('../components/shift-swap/MatchesPanel', () => ({ default: () => <div>matches panel</div> }))
vi.mock('../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

import { ShiftSwapBoard } from './ShiftSwapBoard'

describe('ShiftSwapBoard tablist a11y', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders tabs as an ARIA tablist with one selected tab', async () => {
    render(<ShiftSwapBoard />)
    const tablist = await screen.findByRole('tablist', { name: 'Shift swap views' })
    expect(tablist).toBeInTheDocument()
    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(3)
    const boardTab = screen.getByRole('tab', { name: /All Shifts/ })
    expect(boardTab).toHaveAttribute('aria-selected', 'true')
    expect(boardTab).toHaveAttribute('tabindex', '0')
  })

  it('moves selection with ArrowRight key', async () => {
    render(<ShiftSwapBoard />)
    const tablist = await screen.findByRole('tablist', { name: 'Shift swap views' })
    const boardTab = screen.getByRole('tab', { name: /All Shifts/ })
    expect(boardTab).toHaveAttribute('aria-selected', 'true')
    fireEvent.keyDown(tablist, { key: 'ArrowRight' })
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /My Swaps/ })).toHaveAttribute('aria-selected', 'true')
    })
    expect(screen.getByRole('tabpanel')).toBeInTheDocument()
  })
})
