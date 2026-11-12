/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import RelatedTitlesRail, { isBookishEvent } from '../RelatedTitlesRail'
import type { Event } from '@/api/api'

vi.mock('@/api/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/api/api')
  return {
    ...actual,
    searchCatalog: vi.fn(),
    placeHold: vi.fn(),
  }
})

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'test-jwt' }),
}))

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, fallbackOrParams?: string | Record<string, unknown>) =>
      typeof fallbackOrParams === 'string' ? fallbackOrParams : key,
  }),
}))

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/pages/catalog/components/CatalogItemThumbnail', () => ({
  CatalogCover: ({ title }: { title: string }) => <div data-testid="cover">{title}</div>,
  default: ({ title }: { title: string }) => <div data-testid="thumb">{title}</div>,
}))

import { searchCatalog, placeHold } from '@/api/api'
import toast from 'react-hot-toast'

const mockedSearch = searchCatalog as ReturnType<typeof vi.fn>
const mockedPlaceHold = placeHold as ReturnType<typeof vi.fn>
const mockedToastSuccess = toast.success as ReturnType<typeof vi.fn>

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 1,
    title: 'Spring Book Club',
    description: null,
    start_time: '2026-06-01T18:00:00Z',
    end_time: null,
    location: null,
    is_virtual: false,
    audience: null,
    category: null,
    tags: null,
    max_attendees: null,
    registration_required: false,
    registration_count: 0,
    spots_remaining: null,
    image_url: null,
    is_featured: false,
    series_id: null,
    series_name: null,
    created_at: '2026-05-01T00:00:00Z',
    average_rating: null,
    review_count: 0,
    ...overrides,
  }
}

function makeItem(id: number, overrides: Record<string, unknown> = {}) {
  return {
    id,
    title: `Book ${id}`,
    author: `Author ${id}`,
    item_type: 'book',
    status: 'available',
    isbn: null,
    publisher: null,
    publication_year: null,
    description: null,
    subjects: null,
    cover_url: null,
    page_count: null,
    location: null,
    barcode: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: null,
    is_large_print: false,
    available_for_hold: true,
    images: [],
    series_name: null,
    series_number: null,
    call_number: null,
    dewey_decimal: null,
    total_checkouts: 0,
    director: null,
    actors: null,
    runtime_minutes: null,
    media_format: null,
    content_rating: null,
    disc_count: null,
    studio: null,
    artist: null,
    track_count: null,
    music_genre: null,
    platform: null,
    player_count: null,
    game_genre: null,
    brand: null,
    model_number: null,
    dimensions: null,
    material: null,
    kit_contents: null,
    ...overrides,
  }
}

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('isBookishEvent', () => {
  it('matches book-club tag', () => {
    expect(isBookishEvent(makeEvent({ tags: ['book-club'] }))).toBe(true)
  })
  it('matches storytime category', () => {
    expect(isBookishEvent(makeEvent({ category: 'Storytime' }))).toBe(true)
  })
  it('does not match unrelated events', () => {
    expect(isBookishEvent(makeEvent({ category: 'concert', tags: ['music'] }))).toBe(false)
  })
})

describe('RelatedTitlesRail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders for an event with book-club tag', async () => {
    mockedSearch.mockResolvedValueOnce({
      items: [makeItem(1), makeItem(2), makeItem(3)],
      total: 3, page: 1, per_page: 3, pages: 1,
    })
    render(wrap(<RelatedTitlesRail event={makeEvent({ tags: ['book-club'] })} />))
    expect(await screen.findByTestId('related-titles-list')).toBeInTheDocument()
    expect(screen.getByText('Bring the book to this event')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 4, name: 'Book 1' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Place hold on/i })).toHaveLength(3)
  })

  it('renders for an event with category="storytime"', async () => {
    mockedSearch.mockResolvedValueOnce({
      items: [makeItem(10)],
      total: 1, page: 1, per_page: 3, pages: 1,
    })
    render(wrap(<RelatedTitlesRail event={makeEvent({ category: 'storytime' })} />))
    expect(await screen.findByTestId('related-titles-list')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 4, name: 'Book 10' })).toBeInTheDocument()
  })

  it('renders nothing for an event with no matching tag/category', () => {
    const { container } = render(
      wrap(<RelatedTitlesRail event={makeEvent({ category: 'concert', tags: ['music'] })} />),
    )
    expect(container).toBeEmptyDOMElement()
    expect(mockedSearch).not.toHaveBeenCalled()
  })

  it('renders nothing when catalog query returns 0 results', async () => {
    mockedSearch.mockResolvedValueOnce({
      items: [], total: 0, page: 1, per_page: 3, pages: 0,
    })
    const { container } = render(
      wrap(<RelatedTitlesRail event={makeEvent({ tags: ['book-club'] })} />),
    )
    await waitFor(() => {
      expect(mockedSearch).toHaveBeenCalled()
    })
    await waitFor(() => {
      expect(container).toBeEmptyDOMElement()
    })
  })

  it('renders nothing on catalog query error and logs to console', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    mockedSearch.mockRejectedValueOnce(new Error('boom'))
    const { container } = render(
      wrap(<RelatedTitlesRail event={makeEvent({ tags: ['book-club'] })} />),
    )
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })
    expect(container).toBeEmptyDOMElement()
    consoleSpy.mockRestore()
  })

  it('renders loading skeleton during fetch', async () => {
    let resolveFn: (value: unknown) => void = () => {}
    mockedSearch.mockReturnValueOnce(
      new Promise((resolve) => { resolveFn = resolve }),
    )
    render(wrap(<RelatedTitlesRail event={makeEvent({ tags: ['book-club'] })} />))
    expect(await screen.findByTestId('related-titles-skeleton')).toBeInTheDocument()
    resolveFn({ items: [], total: 0, page: 1, per_page: 3, pages: 0 })
  })

  it('Place Hold button calls hold API and shows confirmation', async () => {
    const user = userEvent.setup()
    mockedSearch.mockResolvedValueOnce({
      items: [makeItem(99)],
      total: 1, page: 1, per_page: 3, pages: 1,
    })
    mockedPlaceHold.mockResolvedValueOnce({ message: 'ok', item_id: 99 })

    render(wrap(<RelatedTitlesRail event={makeEvent({ tags: ['book-club'] })} />))
    const btn = await screen.findByRole('button', { name: /Place hold on Book 99/i })
    await user.click(btn)

    await waitFor(() => {
      expect(mockedPlaceHold).toHaveBeenCalledWith('test-jwt', 99)
    })
    await waitFor(() => {
      expect(mockedToastSuccess).toHaveBeenCalled()
    })
    expect(await screen.findByRole('button', { name: /Place hold on Book 99/i })).toBeDisabled()
  })

  it('requests only holdable titles from the catalog API', async () => {
    mockedSearch.mockResolvedValueOnce({
      items: [makeItem(1, { available_for_hold: true })],
      total: 1, page: 1, per_page: 3, pages: 1,
    })
    render(wrap(<RelatedTitlesRail event={makeEvent({ tags: ['book-club'] })} />))
    await waitFor(() => {
      expect(mockedSearch).toHaveBeenCalledWith(
        expect.objectContaining({ availableForHold: true, per_page: 3, page: 1 }),
      )
    })
  })

  it('renders the holdable items the server returned', async () => {
    mockedSearch.mockResolvedValueOnce({
      items: [
        makeItem(11, { available_for_hold: true, title: 'Holdable One' }),
        makeItem(12, { available_for_hold: true, title: 'Holdable Two' }),
      ],
      total: 2, page: 1, per_page: 3, pages: 1,
    })
    render(wrap(<RelatedTitlesRail event={makeEvent({ tags: ['book-club'] })} />))
    expect(await screen.findByRole('heading', { level: 4, name: 'Holdable One' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { level: 4, name: 'Holdable Two' })).toBeInTheDocument()
  })
})
