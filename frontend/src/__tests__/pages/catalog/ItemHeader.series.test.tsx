/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
*/
/// <reference types="@testing-library/jest-dom/vitest" />
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import { I18nProvider } from '@/i18n/I18nContext'
import { BrandingProvider } from '@/contexts/BrandingContext'
import { ItemHeader } from '@/pages/catalog/components/ItemHeader'
import type { CatalogItem } from '@/api/api'

function makeItem(overrides: Partial<CatalogItem> = {}): CatalogItem {
  return ({
    id: 1,
    title: 'Catching Fire',
    author: 'Suzanne Collins',
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
    series_name: null,
    series_number: null,
    call_number: null,
    dewey_decimal: null,
    total_checkouts: 0,
    ...overrides,
  } as unknown) as CatalogItem
}

function renderHeader(item: CatalogItem) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <BrandingProvider>
        <I18nProvider>
          <MemoryRouter>
            <ItemHeader item={item} simplifiedView={false} showImages={false} />
          </MemoryRouter>
        </I18nProvider>
      </BrandingProvider>
    </QueryClientProvider>,
  )
}

describe('ItemHeader -- series context block', () => {
  it('renders "Part of the X series" linking to the exact series filter', () => {
    renderHeader(makeItem({ series_name: 'The Hunger Games' }))
    const link = screen.getByRole('link', { name: /view all titles in the the hunger games series/i })
    expect(link).toHaveTextContent('Part of the The Hunger Games series')
    expect(link.getAttribute('href')).toBe('/catalog?series_facets=The%20Hunger%20Games')
  })

  it('shows a numbered label when series_number is a bare number', () => {
    renderHeader(makeItem({ series_name: 'The Hunger Games', series_number: '2' }))
    const link = screen.getByRole('link', { name: /view all titles in the the hunger games series/i })
    expect(link).toHaveTextContent('The Hunger Games series · #2')
  })

  it('keeps freeform series_number values as-is', () => {
    renderHeader(makeItem({ series_name: 'Maus', series_number: 'Vol. 2' }))
    const link = screen.getByRole('link', { name: /view all titles in the maus series/i })
    expect(link).toHaveTextContent('Maus series · Vol. 2')
  })

  it('renders no series block when series_name is null', () => {
    renderHeader(makeItem({ series_name: null, series_number: '4' }))
    expect(screen.queryByRole('link', { name: /series/i })).toBeNull()
  })
})
