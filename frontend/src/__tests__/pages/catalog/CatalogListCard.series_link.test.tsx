/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import { I18nProvider } from '@/i18n/I18nContext'
import { BrandingProvider } from '@/contexts/BrandingContext'
import CatalogListCard from '@/pages/catalog/components/CatalogListCard'
import type { CatalogItem } from '@/api/api'

function makeItem(overrides: Partial<CatalogItem> = {}): CatalogItem {
  // Cast to satisfy the structural type without listing every field.
  return ({
    id: 1,
    title: 'Maus I',
    author: 'Art Spiegelman',
    item_type: 'book',
    status: 'available',
    description: null,
    subjects: null,
    cover_url: null,
    page_count: null,
    location: null,
    barcode: null,
    created_at: '2026-01-01',
    updated_at: null,
    is_large_print: false,
    available_for_hold: true,
    images: [],
    series_name: 'Maus',
    series_number: '1',
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
  } as unknown) as CatalogItem
}

function renderCard(item: CatalogItem) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <BrandingProvider>
        <I18nProvider>
          <MemoryRouter>
            <CatalogListCard
              item={item}
              simplifiedView={true}
              quietMode={false}
              showImages={false}
              isSpeaking={false}
              onSpeak={() => {}}
              onStopSpeak={() => {}}
            />
          </MemoryRouter>
        </I18nProvider>
      </BrandingProvider>
    </QueryClientProvider>,
  )
}

describe('CatalogListCard -- series link', () => {
  it('renders series_name as a link to /catalog?series_facets=<name>', () => {
    renderCard(makeItem({ series_name: 'Maus' }))
    const link = screen.getByRole('link', { name: /view all in series: maus/i })
    expect(link.getAttribute('href')).toBe('/catalog?series_facets=Maus')
  })

  it('URL-encodes series names with special characters', () => {
    renderCard(makeItem({ series_name: 'A & B' }))
    const link = screen.getByRole('link', { name: /view all in series: a & b/i })
    expect(link.getAttribute('href')).toBe('/catalog?series_facets=A%20%26%20B')
  })

  it('does not render series link when series_name is null', () => {
    renderCard(makeItem({ series_name: null }))
    expect(screen.queryByRole('link', { name: /view all in series/i })).toBeNull()
  })

  it('series link is a sibling of the card link, not nested inside an anchor', () => {
    // Overlay-link pattern: the card link no longer wraps the card content,
    // so the series link must not sit inside any anchor. Clicking it can
    // only ever trigger its own navigation — no stopPropagation needed.
    renderCard(makeItem({ series_name: 'Maus' }))
    const link = screen.getByRole('link', { name: /view all in series: maus/i })
    expect(link.parentElement?.closest('a')).toBeNull()
  })
})
