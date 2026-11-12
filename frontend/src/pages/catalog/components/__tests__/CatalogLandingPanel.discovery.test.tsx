/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import CatalogLandingPanel from '../CatalogLandingPanel'

vi.mock('@/i18n/I18nContext', () => ({ useTranslation: () => ({ t: (key: string, fallback?: string) => fallback ?? key }) }))
vi.mock('../RecentlyViewedRow', () => ({ default: () => <a href="/catalog/2">Previously opened book</a> }))
vi.mock('../NewArrivalsRow', () => ({ default: () => null }))
vi.mock('../StaffPicksSection', () => ({ default: () => null }))
vi.mock('../MoodBrowseRow', () => ({ default: () => null }))
vi.mock('@/components/reading-lists/YourListsSection', () => ({ YourListsSection: () => null }))
vi.mock('../CatalogGridCard', () => ({ default: ({ item }: { item: { title: string } }) => <a href="/catalog/1">{item.title}</a> }))
vi.mock('../CatalogListCard', () => ({ default: ({ item }: { item: { title: string } }) => <a href="/catalog/1">{item.title}</a> }))

function setup(quiet = false) {
  const props: React.ComponentProps<typeof CatalogLandingPanel> = {
    filteredItems: [{ id: 1, title: 'A catalog result', source: 'catalog' } as never],
    activeFormat: null, onBrowseFormat: vi.fn(), effectiveQuietMode: quiet,
    effectiveSimplifiedView: false, effectiveShowImages: true, speakingItemId: null,
    onSpeak: vi.fn(), onStopSpeak: vi.fn(), viewMode: 'grid', readingLists: [], hasData: true,
  }
  return render(<MemoryRouter><CatalogLandingPanel {...props} /></MemoryRouter>)
}

describe('catalog landing discovery', () => {
  it('shows results immediately and reveals reading history only when requested', () => {
    setup()
    expect(screen.getByRole('link', { name: 'A catalog result' })).toBeVisible()
    const history = screen.getByRole('link', { name: 'Previously opened book' })
    expect(history.closest('details')).not.toHaveAttribute('open')
    expect(screen.getByRole('link', { name: 'A catalog result' }).closest('details')).toBeNull()
    fireEvent.click(screen.getByText('Browse reading collections'))
    expect(history.closest('details')).toHaveAttribute('open')
  })
  it('keeps quiet mode free of optional discovery sections', () => {
    setup(true)
    expect(screen.getByRole('link', { name: 'A catalog result' })).toBeVisible()
    expect(screen.queryByText('Browse reading collections')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Previously opened book' })).not.toBeInTheDocument()
  })
})
