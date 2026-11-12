/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
    language: 'en',
  }),
}))

const getNewArrivals = vi.fn()
vi.mock('@/api/domains/catalog/catalog-api', () => ({
  getNewArrivals: (...args: unknown[]) => getNewArrivals(...args),
}))

const getPublicStaffPicksLists = vi.fn()
const getPublicStaffPicksList = vi.fn()
vi.mock('@/api/domains/content/staff-picks-api', () => ({
  getPublicStaffPicksLists: (...args: unknown[]) => getPublicStaffPicksLists(...args),
  getPublicStaffPicksList: (...args: unknown[]) => getPublicStaffPicksList(...args),
}))

import HomeBookShelves from '@/components/HomeBookShelves'

const LISTS = [
  { id: 4, title: "Sam's Camping Reads 2026", description: null, is_active: true, display_order: 0, created_by_id: 1, items_count: 0, created_at: null },
  { id: 1, title: "Sam's Summer Picks", description: 'Director Sam picks', is_active: true, display_order: 1, created_by_id: 1, items_count: 0, created_at: null },
  { id: 2, title: "Children's Favorites", description: null, is_active: true, display_order: 2, created_by_id: 9, items_count: 0, created_at: null },
  { id: 3, title: 'Teen Must-Reads', description: null, is_active: true, display_order: 3, created_by_id: 10, items_count: 0, created_at: null },
]

function detailFor(id: number) {
  const list = LISTS.find((l) => l.id === id)!
  return {
    ...list,
    items: [
      {
        id: id * 10 + 1,
        catalog_item_id: id * 100 + 1,
        catalog_item: { id: id * 100 + 1, title: `Book ${id}A`, author: 'Author', cover_url: null },
        staff_notes: null,
        display_order: 0,
      },
    ],
  }
}

function renderShelves() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <HomeBookShelves />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  getNewArrivals.mockResolvedValue({ items: [{ id: 999, title: 'Fresh Arrival', author: 'A', cover_url: null }] })
  getPublicStaffPicksLists.mockResolvedValue(LISTS)
  getPublicStaffPicksList.mockImplementation((id: number) => Promise.resolve(detailFor(id)))
})

describe('HomeBookShelves on /picks', () => {
  it('renders every active collection as its own shelf, not just the first', async () => {
    renderShelves()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: "Sam's Camping Reads 2026" })).toBeInTheDocument()
    })
    expect(screen.getByRole('heading', { name: "Sam's Summer Picks" })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: "Children's Favorites" })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Teen Must-Reads' })).toBeInTheDocument()
  })

  it('requests more than one list (no hard limit of 1)', async () => {
    renderShelves()
    await waitFor(() => expect(getPublicStaffPicksLists).toHaveBeenCalled())
    const limitArg = getPublicStaffPicksLists.mock.calls[0]?.[0] as number
    expect(limitArg).toBeGreaterThan(1)
  })
})
