/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from 'vitest'
import { loadLanguage, getTranslation } from '@/i18n/translations'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import BookClubsPage, { formatMemberSummary, deriveGenres } from '../BookClubsPage'
import type { BookClubListItem } from '@/api/book-clubs-api'

vi.mock('@/i18n', async () => {
  const actual = await vi.importActual<typeof import('@/i18n')>('@/i18n')
  return {
    ...actual,
    t: (key: string, params?: Record<string, unknown> | string) =>
      typeof params === 'string'
        ? getTranslation(key, 'en', undefined, params)
        : getTranslation(key, 'en', params),
  }
})

vi.mock('@/hooks/usePageTitle', () => ({
  usePageTitle: () => undefined,
}))

vi.mock('@/contexts/BrandingContext', () => ({
  useBranding: () => ({ library_short_name: 'Test Library' }),
}))

// Waitlist flag toggle for capacity-badge tests. Default OFF.
let waitlistFlag = false
vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({
    isFeatureEnabled: (name: string) =>
      name === 'book_club_waitlist_enabled' ? waitlistFlag : false,
  }),
}))

// listBookClubs is the only API call the page now makes. Mockable per-test
// via the captured mock below.
const listBookClubsMock = vi.fn()
vi.mock('@/api/book-clubs-api', async () => {
  const actual = await vi.importActual<typeof import('@/api/book-clubs-api')>(
    '@/api/book-clubs-api',
  )
  return {
    ...actual,
    listBookClubs: (...args: unknown[]) => listBookClubsMock(...args),
  }
})

function buildClub(partial: Partial<BookClubListItem> & { id: number; name: string }): BookClubListItem {
  return {
    description: null,
    genre: null,
    meeting_frequency: null,
    member_count: 0,
    max_members: null,
    current_member_count: 0,
    waitlist_count: 0,
    is_full: false,
    current_book_title: null,
    current_book_author: null,
    is_member: false,
    next_meeting_date: null,
    ...partial,
  }
}

function renderPage() {
  return render(
    <MemoryRouter>
      <BookClubsPage />
    </MemoryRouter>,
  )
}

beforeAll(async () => {
  await loadLanguage('en')
})

describe('formatMemberSummary', () => {
  it('renders capacity suffix when max_members is set', () => {
    expect(formatMemberSummary(7, 12)).toBe('7 members · capacity 12')
  })
  it('omits capacity when max_members is null', () => {
    expect(formatMemberSummary(7, null)).toBe('7 members')
  })
  it('omits capacity when max_members is undefined', () => {
    expect(formatMemberSummary(0, undefined)).toBe('0 members')
  })
  it('renders capacity even when at 0 members', () => {
    expect(formatMemberSummary(0, 5)).toBe('0 members · capacity 5')
  })
})

describe('deriveGenres', () => {
  it('returns empty array when no club has a genre', () => {
    expect(deriveGenres([{ genre: null }, { genre: null }])).toEqual([])
  })
  it('dedupes case-insensitively, preserving first-seen casing', () => {
    expect(deriveGenres([
      { genre: 'Fiction' },
      { genre: 'fiction' },
      { genre: 'MYSTERY' },
      { genre: 'mystery' },
    ])).toEqual(['Fiction', 'MYSTERY'])
  })
  it('drops null/empty genres', () => {
    expect(deriveGenres([
      { genre: null },
      { genre: 'Romance' },
      { genre: '' },
      { genre: 'Nonfiction' },
    ])).toEqual(['Romance', 'Nonfiction'])
  })
})

describe('BookClubsPage', () => {
  beforeEach(() => {
    listBookClubsMock.mockReset()
  })
  afterEach(() => {
    // Defensive: ensure fake timers never leak into a subsequent test.
    vi.useRealTimers()
  })

  it('hides the genre pills row when no club has a genre', async () => {
    listBookClubsMock.mockResolvedValue({
      clubs: [
        buildClub({ id: 1, name: 'Tuesday Reads' }),
        buildClub({ id: 2, name: 'Saturday Stories' }),
      ],
      total: 2,
    })
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Tuesday Reads')).toBeInTheDocument()
    })
    expect(screen.queryByRole('radiogroup', { name: /filter by genre/i })).not.toBeInTheDocument()
  })

  it('shows genre pills only for genres that exist in the loaded clubs', async () => {
    listBookClubsMock.mockResolvedValue({
      clubs: [
        buildClub({ id: 1, name: 'A', genre: 'Fiction' }),
        buildClub({ id: 2, name: 'B', genre: null }),
      ],
      total: 2,
    })
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('A')).toBeInTheDocument()
    })
    const group = screen.getByRole('radiogroup', { name: /filter by genre/i })
    expect(group).toBeInTheDocument()
    // "All" + "Fiction" only -- no Mystery / Non-Fiction
    expect(screen.getByRole('radio', { name: 'All' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Fiction' })).toBeInTheDocument()
    expect(screen.queryByRole('radio', { name: 'Mystery' })).not.toBeInTheDocument()
    expect(screen.queryByRole('radio', { name: 'Non-Fiction' })).not.toBeInTheDocument()
  })

  it('filters cards by the search input on name or description', async () => {
    listBookClubsMock.mockResolvedValue({
      clubs: [
        buildClub({ id: 1, name: 'Mystery Monday', description: 'Whodunits and noir' }),
        buildClub({ id: 2, name: 'Garden Club', description: 'Botanical readings' }),
      ],
      total: 2,
    })
    renderPage()
    // initial render: both cards
    await waitFor(() => {
      expect(screen.getByText('Mystery Monday')).toBeInTheDocument()
      expect(screen.getByText('Garden Club')).toBeInTheDocument()
    })
    const input = screen.getByPlaceholderText(/searchBookClubs|search/i)
    fireEvent.change(input, { target: { value: 'noir' } })
    // Real debounce (~200ms) -- waitFor polls with real timers.
    await waitFor(
      () => {
        expect(screen.queryByText('Garden Club')).not.toBeInTheDocument()
      },
      { timeout: 1500 },
    )
    expect(screen.getByText('Mystery Monday')).toBeInTheDocument()

    // no-match query shows the search-empty message
    fireEvent.change(input, { target: { value: 'zzzzz' } })
    await waitFor(
      () => {
        expect(screen.getByText(/No clubs match/i)).toBeInTheDocument()
      },
      { timeout: 1500 },
    )
  })

  it('renders the spec capacity badge "N/Max members" when capped and not full', async () => {
    listBookClubsMock.mockResolvedValue({
      clubs: [
        buildClub({
          id: 1,
          name: 'Capped Club',
          member_count: 7,
          current_member_count: 7,
          max_members: 12,
        }),
      ],
      total: 1,
    })
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('7/12 members')).toBeInTheDocument()
    })
    expect(screen.queryByText(/capacity 12/)).not.toBeInTheDocument()
  })

  it('renders "Full" (no waiting count) when full but waitlist flag is OFF', async () => {
    waitlistFlag = false
    listBookClubsMock.mockResolvedValue({
      clubs: [
        buildClub({
          id: 1,
          name: 'Full Club',
          member_count: 12,
          current_member_count: 12,
          max_members: 12,
          waitlist_count: 3,
          is_full: true,
        }),
      ],
      total: 1,
    })
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Full')).toBeInTheDocument()
    })
    expect(screen.queryByText(/waiting/i)).not.toBeInTheDocument()
  })

  it('renders "Full · N waiting" when full and waitlist flag is ON', async () => {
    waitlistFlag = true
    listBookClubsMock.mockResolvedValue({
      clubs: [
        buildClub({
          id: 1,
          name: 'Full Club',
          member_count: 12,
          current_member_count: 12,
          max_members: 12,
          waitlist_count: 3,
          is_full: true,
        }),
      ],
      total: 1,
    })
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Full · 3 waiting')).toBeInTheDocument()
    })
    waitlistFlag = false
  })

  it('renders the member-count label without capacity when max_members is null', async () => {
    listBookClubsMock.mockResolvedValue({
      clubs: [
        buildClub({ id: 1, name: 'Open Club', member_count: 4, max_members: null }),
      ],
      total: 1,
    })
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('4 members')).toBeInTheDocument()
    })
    expect(screen.queryByText(/capacity/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/\d+\/\d+ members/)).not.toBeInTheDocument()
  })
})
