/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="@testing-library/jest-dom/vitest" />
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '@/i18n/I18nContext'
import { BrandingProvider } from '@/contexts/BrandingContext'
import { SeriesReadingOrder } from '@/pages/catalog/components/SeriesReadingOrder'
import type { CatalogItem, SeriesReadingOrder as SeriesData } from '@/api/api'

function makeItem(overrides: Partial<CatalogItem> = {}): CatalogItem {
  return ({
    id: 4,
    title: 'Book Four',
    author: 'Author',
    item_type: 'book',
    status: 'available',
    series_name: 'Reading Order Test',
    series_number: '4',
    series_position: 4,
    cover_url: null,
    ...overrides,
  } as unknown) as CatalogItem
}

function makeSeries(overrides: Partial<SeriesData> = {}): SeriesData {
  return {
    series_name: 'Reading Order Test',
    total_held: 3,
    current_position: 4,
    prev_id: 1,
    next_id: 7,
    items: [
      { id: 1, title: 'Book One', author: 'Author', item_type: 'book', series_position: 1, series_number: '1', cover_url: null, status: 'available' },
      { id: 4, title: 'Book Four', author: 'Author', item_type: 'book', series_position: 4, series_number: '4', cover_url: null, status: 'available' },
      { id: 7, title: 'Book Seven', author: 'Author', item_type: 'book', series_position: 7, series_number: '7', cover_url: null, status: 'available' },
    ],
    ...overrides,
  }
}

function renderBlock(item: CatalogItem, series: SeriesData | undefined) {
  return render(
    <BrandingProvider>
      <I18nProvider>
        <MemoryRouter>
          <SeriesReadingOrder item={item} series={series} />
        </MemoryRouter>
      </I18nProvider>
    </BrandingProvider>,
  )
}

describe('SeriesReadingOrder', () => {
  it('shows "Book N in [series]" when a parsed position is present', () => {
    renderBlock(makeItem(), makeSeries())
    expect(screen.getByText(/Book 4 in Reading Order Test/i)).toBeInTheDocument()
  })

  it('describes the list as our-catalog holdings, not the full series', () => {
    renderBlock(makeItem(), makeSeries())
    // Honesty bar: never claims series length, frames it as what we hold.
    expect(screen.getByText(/titles in this series that are in our catalog/i)).toBeInTheDocument()
  })

  it('links prev/next to adjacent held titles by position (sparse holdings)', () => {
    renderBlock(makeItem(), makeSeries())
    const prev = screen.getByRole('link', { name: /previous title in our catalog: book one/i })
    const next = screen.getByRole('link', { name: /next title in our catalog: book seven/i })
    expect(prev.getAttribute('href')).toBe('/catalog/1')
    expect(next.getAttribute('href')).toBe('/catalog/7')
  })

  it('renders a view-all link to the full series browse', () => {
    renderBlock(makeItem(), makeSeries())
    const viewAll = screen.getByRole('link', { name: /view all titles in this series/i })
    expect(viewAll.getAttribute('href')).toBe('/catalog?series_facets=Reading%20Order%20Test')
  })

  it('omits the missing neighbour link when at the start of held titles', () => {
    const item = makeItem({ id: 1, title: 'Book One', series_number: '1', series_position: 1 })
    const series = makeSeries({ current_position: 1, prev_id: null, next_id: 4 })
    renderBlock(item, series)
    expect(screen.queryByRole('link', { name: /previous title in our catalog/i })).toBeNull()
    expect(screen.getByRole('link', { name: /next title in our catalog: book four/i })).toBeInTheDocument()
  })

  it('renders nothing when the item has no parsed position (fallback to ItemHeader chip)', () => {
    const item = makeItem({ series_position: null, series_number: 'Special' })
    const { container } = renderBlock(item, undefined)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders nothing when the series payload is absent', () => {
    const { container } = renderBlock(makeItem(), undefined)
    expect(container).toBeEmptyDOMElement()
  })
})
