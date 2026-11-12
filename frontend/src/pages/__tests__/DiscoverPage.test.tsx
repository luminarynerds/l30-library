/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Page-level tests for the front-door Discover page: New Arrivals rail
 * (via CatalogShelf), reader-shelf doorways, and the two closing doorways.
 */
import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { loadLanguage } from '@/i18n/translations'
import { I18nProvider } from '@/i18n/I18nContext'
import { BrandingProvider } from '@/contexts/BrandingContext'
import { getNewArrivals } from '@/api/domains/catalog/catalog-api'
import { getDiscoverShelves } from '@/api/discover-shelves-api'
import DiscoverPage from '../DiscoverPage'

vi.mock('@/api/domains/catalog/catalog-api', () => ({ getNewArrivals: vi.fn() }))
vi.mock('@/api/discover-shelves-api', () => ({ getDiscoverShelves: vi.fn() }))

const mockNewArrivals = vi.mocked(getNewArrivals)
const mockShelves = vi.mocked(getDiscoverShelves)

beforeAll(async () => {
  await loadLanguage('en')
})

beforeEach(() => {
  mockNewArrivals.mockResolvedValue({ items: [], total: 0, days: 30, period: 'month' })
  mockShelves.mockResolvedValue([])
})

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <BrandingProvider>
        <I18nProvider>
          <MemoryRouter>
            <DiscoverPage />
          </MemoryRouter>
        </I18nProvider>
      </BrandingProvider>
    </QueryClientProvider>,
  )
}

describe('DiscoverPage front door', () => {
  it('renders the page heading', async () => {
    renderPage()
    expect(await screen.findByRole('heading', { level: 1, name: 'Discover' })).toBeTruthy()
  })

  it('renders a New Arrivals rail with mapped items when the API returns some', async () => {
    mockNewArrivals.mockResolvedValue({
      items: [
        { id: 11, title: 'The Berry Pickers', author: 'Amanda Peters', item_type: 'book', status: 'available', cover_url: null, page_count: 320 },
        { id: 12, title: 'Pachinko', author: 'Min Jin Lee', item_type: 'book', status: 'checked_out', cover_url: null, page_count: 496 },
      ] as never,
      total: 2, days: 30, period: 'month',
    })
    renderPage()
    expect(await screen.findByRole('heading', { name: 'New Arrivals' })).toBeTruthy()
    expect(screen.getByRole('link', { name: /The Berry Pickers/ })).toBeTruthy()
    expect(screen.getByRole('link', { name: /Pachinko/ })).toBeTruthy()
  })

  it('hides the New Arrivals rail entirely when the API returns none (no dead band)', async () => {
    mockNewArrivals.mockResolvedValue({ items: [], total: 0, days: 30, period: 'month' })
    renderPage()
    // Page still renders; the rail heading must be absent.
    await screen.findByRole('heading', { level: 1, name: 'Discover' })
    expect(screen.queryByRole('heading', { name: 'New Arrivals' })).toBeNull()
    expect(screen.queryByText('Check back soon for new arrivals')).toBeNull()
  })

  it('renders reader-shelf doorways linking to /catalog?shelf= with accessible names', async () => {
    mockShelves.mockResolvedValue([
      { id: 1, slug: 'local-ohio-authors', title: 'Local Ohio authors', description: null, audience: 'all', display_order: 1, item_count: 8 },
      { id: 2, slug: 'cozy-mysteries', title: 'Cozy mysteries', description: null, audience: 'adults', display_order: 2, item_count: 1 },
    ])
    renderPage()
    const local = await screen.findByRole('link', { name: 'Local Ohio authors shelf, 8 titles' })
    expect(local.getAttribute('href')).toBe('/catalog?shelf=local-ohio-authors')
    // Singular pluralization for a 1-count shelf.
    expect(screen.getByRole('link', { name: 'Cozy mysteries shelf, 1 title' })).toBeTruthy()
  })

  it('omits shelves with zero items and hides the section when none qualify', async () => {
    mockShelves.mockResolvedValue([
      { id: 3, slug: 'empty', title: 'Empty shelf', description: null, audience: 'all', display_order: 1, item_count: 0 },
    ])
    renderPage()
    await screen.findByRole('heading', { level: 1, name: 'Discover' })
    expect(screen.queryByRole('heading', { name: 'Reader shelves' })).toBeNull()
  })

  it('renders the two closing doorways under a Keep exploring heading', async () => {
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Keep exploring' })).toBeTruthy()
    const picks = screen.getByRole('link', { name: /curated picks/i })
    const catalog = screen.getByRole('link', { name: /full catalog/i })
    expect(picks.getAttribute('href')).toBe('/picks')
    expect(catalog.getAttribute('href')).toBe('/catalog')
  })
})
