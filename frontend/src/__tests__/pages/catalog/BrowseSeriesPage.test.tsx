/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
*/
/// <reference types="@testing-library/jest-dom/vitest" />
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import { I18nProvider } from '@/i18n/I18nContext'
import { BrandingProvider } from '@/contexts/BrandingContext'
import BrowseSeriesPage from '@/pages/catalog/BrowseSeriesPage'
import { searchCatalog } from '@/api/api'

vi.mock('@/api/api', () => ({
  searchCatalog: vi.fn(),
}))

const mockedSearchCatalog = vi.mocked(searchCatalog)

function makeResult(series: { value: string; count: number }[]) {
  return {
    items: [],
    total: 0,
    page: 1,
    per_page: 1,
    pages: 0,
    facets: { item_type: [], status: [], publication_year: [], location: [], series },
  } as Awaited<ReturnType<typeof searchCatalog>>
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <BrandingProvider>
        <I18nProvider>
          <MemoryRouter>
            <BrowseSeriesPage />
          </MemoryRouter>
        </I18nProvider>
      </BrandingProvider>
    </QueryClientProvider>,
  )
}

describe('BrowseSeriesPage -- server series facets', () => {
  beforeEach(() => {
    mockedSearchCatalog.mockReset()
  })

  it('requests facets (not 1000 items) and renders one card per series facet', async () => {
    mockedSearchCatalog.mockResolvedValue(makeResult([
      { value: 'Maus', count: 2 },
      { value: 'The Hunger Games', count: 3 },
    ]))
    renderPage()

    expect(await screen.findByText('Maus')).toBeInTheDocument()
    expect(screen.getByText('The Hunger Games')).toBeInTheDocument()
    expect(screen.getByText('2 titles')).toBeInTheDocument()
    expect(screen.getByText('3 titles')).toBeInTheDocument()
    expect(mockedSearchCatalog).toHaveBeenCalledWith({ per_page: 1, include_facets: true })
  })

  it('links each series to the exact-match series_facets catalog filter', async () => {
    mockedSearchCatalog.mockResolvedValue(makeResult([{ value: 'A & B', count: 1 }]))
    renderPage()

    const link = await screen.findByRole('link', { name: 'A & B' })
    expect(link.getAttribute('href')).toBe('/catalog?series_facets=A%20%26%20B')
  })

  it('filters the facet list client-side by series name', async () => {
    mockedSearchCatalog.mockResolvedValue(makeResult([
      { value: 'Maus', count: 2 },
      { value: 'Dune', count: 5 },
    ]))
    renderPage()
    await screen.findByText('Maus')

    await userEvent.type(screen.getByRole('textbox', { name: /search series/i }), 'dune')
    expect(screen.queryByText('Maus')).toBeNull()
    expect(screen.getByText('Dune')).toBeInTheDocument()
  })

  it('shows the no-series empty state when the catalog has no series facets', async () => {
    mockedSearchCatalog.mockResolvedValue(makeResult([]))
    renderPage()

    expect(await screen.findByText('No series found')).toBeInTheDocument()
    expect(screen.getByText(/no items in the catalog have series information/i)).toBeInTheDocument()
  })
})
