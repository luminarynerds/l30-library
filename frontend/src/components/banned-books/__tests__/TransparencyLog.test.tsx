/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import TransparencyLog from '../TransparencyLog'
import {
  getPublicChallenges,
  getPublicStats,
  type BookChallengePublic,
  type BookChallengePublicListResponse,
  type BookChallengeStats,
} from '@/api/domains/content/book-challenges-api'

vi.mock('@/api/domains/content/book-challenges-api', async () => {
  const actual = await vi.importActual<
    typeof import('@/api/domains/content/book-challenges-api')
  >('@/api/domains/content/book-challenges-api')
  return {
    ...actual,
    getPublicChallenges: vi.fn(),
    getPublicStats: vi.fn(),
  }
})

const mockedGetPublicChallenges = getPublicChallenges as unknown as ReturnType<typeof vi.fn>
const mockedGetPublicStats = getPublicStats as unknown as ReturnType<typeof vi.fn>

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  })
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>
}

function makeItem(
  overrides: Partial<BookChallengePublic> = {},
): BookChallengePublic {
  return {
    id: 1,
    catalog_item_id: null,
    public_title: null,
    title: 'Sample Title',
    author: 'Sample Author',
    primary_reason: 'language',
    outcome: 'retained',
    public_summary: 'Sample summary',
    lessons_learned: null,
    date_received: '2024-06-01T00:00:00Z',
    date_resolved: '2024-07-01T00:00:00Z',
    ...overrides,
  }
}

function makeEnvelope(
  items: BookChallengePublic[],
  overrides: Partial<BookChallengePublicListResponse> = {},
): BookChallengePublicListResponse {
  return {
    items,
    total: items.length,
    page: 1,
    per_page: 10,
    pages: 1,
    ...overrides,
  }
}

const DEFAULT_STATS: BookChallengeStats = {
  total_challenges: 3,
  pending_challenges: 0,
  resolved_this_year: 3,
  outcomes: { retained: 2, removed: 1 },
  reasons: { language: 2, lgbtq_content: 1 },
  available_years: [2024, 2023],
}

describe('TransparencyLog', () => {
  beforeEach(() => {
    mockedGetPublicChallenges.mockReset()
    mockedGetPublicStats.mockReset()
    mockedGetPublicStats.mockResolvedValue(DEFAULT_STATS)
  })

  it('renders filter dropdowns populated from stats', async () => {
    mockedGetPublicChallenges.mockResolvedValue(makeEnvelope([makeItem()]))

    render(wrap(<TransparencyLog />))

    // Year dropdown populated from stats.available_years
    const yearSelect = await screen.findByLabelText('Year')
    expect(yearSelect).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByRole('option', { name: '2024' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: '2023' })).toBeInTheDocument()
    })

    // Outcome dropdown populated from stats.outcomes keys
    expect(screen.getByLabelText('Outcome')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Retained' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Removed' })).toBeInTheDocument()

    // Reason dropdown populated from stats.reasons keys
    expect(screen.getByLabelText('Reason')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Language' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'LGBTQ+ Content' })).toBeInTheDocument()
  })

  it('selecting a filter triggers a new fetch with the right params', async () => {
    mockedGetPublicChallenges.mockResolvedValue(makeEnvelope([makeItem()]))

    render(wrap(<TransparencyLog />))

    // Wait for initial fetch (page=1, no filters)
    await waitFor(() => {
      expect(mockedGetPublicChallenges).toHaveBeenCalled()
    })
    const firstCall = mockedGetPublicChallenges.mock.calls[0]![0]
    expect(firstCall).toMatchObject({ page: 1 })
    expect(firstCall.outcome).toBeUndefined()

    // Change outcome filter
    const outcomeSelect = await screen.findByLabelText('Outcome')
    fireEvent.change(outcomeSelect, { target: { value: 'removed' } })

    await waitFor(() => {
      const calls = mockedGetPublicChallenges.mock.calls
      expect(calls.length).toBeGreaterThan(1)
      const lastCall = calls[calls.length - 1]![0]
      expect(lastCall.outcome).toBe('removed')
      expect(lastCall.page).toBe(1)
    })
  })

  it('reset clears all filters and refetches', async () => {
    mockedGetPublicChallenges.mockResolvedValue(makeEnvelope([makeItem()]))

    render(wrap(<TransparencyLog />))

    const outcomeSelect = await screen.findByLabelText('Outcome')
    // Wait for the stats-driven options to populate before selecting one;
    // jsdom silently ignores a value with no matching <option>.
    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Removed' })).toBeInTheDocument()
    })
    fireEvent.change(outcomeSelect, { target: { value: 'removed' } })

    await waitFor(() => {
      const lastCall = mockedGetPublicChallenges.mock.calls.slice(-1)[0]![0]
      expect(lastCall.outcome).toBe('removed')
    })

    const resetButton = screen.getByRole('button', { name: 'Reset' })
    fireEvent.click(resetButton)

    await waitFor(() => {
      const lastCall = mockedGetPublicChallenges.mock.calls.slice(-1)[0]![0]
      expect(lastCall.outcome).toBeUndefined()
      expect(lastCall.year).toBeUndefined()
      expect(lastCall.reason).toBeUndefined()
    })
  })

  it('Next/Previous pagination advances and clamps to the page range', async () => {
    mockedGetPublicChallenges.mockResolvedValue(
      makeEnvelope([makeItem(), makeItem({ id: 2 })], {
        total: 25,
        per_page: 10,
        pages: 3,
      }),
    )

    render(wrap(<TransparencyLog />))

    const nextButton = await screen.findByRole('button', { name: 'Next' })
    const prevButton = screen.getByRole('button', { name: 'Previous' })

    // On page 1, Previous is disabled.
    expect(prevButton).toBeDisabled()

    fireEvent.click(nextButton)
    await waitFor(() => {
      const lastCall = mockedGetPublicChallenges.mock.calls.slice(-1)[0]![0]
      expect(lastCall.page).toBe(2)
    })
    // "Page 2 of 3" is announced.
    expect(screen.getByText(/Page 2 of 3/)).toBeInTheDocument()
  })

  it('hides pagination when total <= per_page', async () => {
    mockedGetPublicChallenges.mockResolvedValue(
      makeEnvelope([makeItem()], { total: 1, per_page: 10, pages: 1 }),
    )

    render(wrap(<TransparencyLog />))

    await screen.findByText('Sample Title')
    expect(screen.queryByRole('button', { name: 'Next' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Previous' })).not.toBeInTheDocument()
  })

  it('suppresses author rendering when the API omits it (public_title set)', async () => {
    mockedGetPublicChallenges.mockResolvedValue(
      makeEnvelope([
        makeItem({
          id: 10,
          title: 'Real Internal Title',
          public_title: 'YA Nonfiction Challenge -- Retained',
          author: null, // server suppressed it because public_title is set
        }),
        makeItem({
          id: 11,
          title: 'Visible Title',
          public_title: null,
          author: 'Visible Author',
        }),
      ]),
    )

    render(wrap(<TransparencyLog />))

    // Public title surfaces; author for the suppressed row does not.
    expect(
      await screen.findByText('YA Nonfiction Challenge -- Retained'),
    ).toBeInTheDocument()
    expect(screen.queryByText(/by .*Famous/i)).not.toBeInTheDocument()
    // The unsuppressed author still shows.
    expect(screen.getByText(/by Visible Author/)).toBeInTheDocument()
  })

  it('renders an empty state when no rows match', async () => {
    mockedGetPublicChallenges.mockResolvedValue(
      makeEnvelope([], { total: 0, page: 1, per_page: 10, pages: 1 }),
    )

    render(wrap(<TransparencyLog />))

    expect(
      await screen.findByText(/No public challenges have been recorded yet/i),
    ).toBeInTheDocument()
  })

  it('renders an error state when the fetch fails', async () => {
    mockedGetPublicChallenges.mockRejectedValue(new Error('boom'))

    render(wrap(<TransparencyLog />))

    expect(
      await screen.findByText(/We couldn't load the Transparency Log/i),
    ).toBeInTheDocument()
  })
})
