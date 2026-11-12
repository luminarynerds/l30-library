/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Same-work matching for the related-formats hook (feeds PlaceHoldModal
 * format dropdown). Matching must be exact normalized title + author --
 * substring matching let "Emma" pull in "Emma in the Night" and hand
 * patrons a hold on the wrong work.
 */
import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useRelatedFormats } from '../useRelatedFormats'
import type { CatalogItem } from '@/api/api'

vi.mock('@/api/api', async () => {
  const actual = await vi.importActual<object>('@/api/api')
  return { ...actual, searchCatalog: vi.fn() }
})
import { searchCatalog } from '@/api/api'

function makeItem(overrides: Partial<CatalogItem>): CatalogItem {
  return {
    id: 1,
    title: 'Emma',
    author: 'Jane Austen',
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
    ...overrides,
  } as CatalogItem
}

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

function mockResults(items: CatalogItem[]) {
  vi.mocked(searchCatalog).mockResolvedValue({
    items,
    total: items.length,
    page: 1,
    per_page: 20,
    pages: 1,
  } as Awaited<ReturnType<typeof searchCatalog>>)
}

describe('useRelatedFormats same-work matching', () => {
  beforeEach(() => {
    vi.mocked(searchCatalog).mockReset()
  })

  it('excludes substring title matches and different authors; keeps exact same work', async () => {
    const current = makeItem({ id: 1, title: 'Emma', author: 'Jane Austen' })
    mockResults([
      // exact same work, different format -> KEEP (normalization tolerant)
      makeItem({ id: 2, title: ' emma ', author: 'JANE  AUSTEN', item_type: 'audiobook' }),
      // substring title, different work -> DROP
      makeItem({ id: 3, title: 'Emma in the Night', author: 'Wendy Walker', item_type: 'ebook' }),
      // same title, different author -> DROP
      makeItem({ id: 4, title: 'Emma', author: 'Someone Else', item_type: 'dvd' }),
      // author substring (old bidirectional includes bug) -> DROP
      makeItem({ id: 5, title: 'Emma', author: 'Jane Austen Society', item_type: 'cd' }),
    ])

    const { result } = renderHook(() => useRelatedFormats(current), {
      wrapper: makeWrapper(),
    })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    await waitFor(() => expect(result.current.formats.length).toBe(2))

    const ids = result.current.formats.map((f) => f.id)
    expect(ids).toEqual([1, 2]) // current item + exact-work audiobook only
    expect(result.current.formats[0]?.isCurrent).toBe(true)
    expect(result.current.formats[1]?.item_type).toBe('audiobook')
  })

  it('never includes the item itself twice', async () => {
    const current = makeItem({ id: 1 })
    mockResults([makeItem({ id: 1 })])

    const { result } = renderHook(() => useRelatedFormats(current), {
      wrapper: makeWrapper(),
    })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.formats.map((f) => f.id)).toEqual([1])
  })

  it('dedupes to one entry per format', async () => {
    const current = makeItem({ id: 1 })
    mockResults([
      makeItem({ id: 2, item_type: 'audiobook', status: 'checked_out' }),
      makeItem({ id: 3, item_type: 'audiobook', status: 'available' }),
    ])

    const { result } = renderHook(() => useRelatedFormats(current), {
      wrapper: makeWrapper(),
    })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    await waitFor(() => expect(result.current.formats.length).toBe(2))
    // available copy preferred for the audiobook slot
    expect(result.current.formats[1]?.id).toBe(3)
  })
})
