/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AdminCollectionMemoryPage from '@/pages/AdminCollectionMemoryPage'

const STRINGS: Record<string, string> = {
  'collectionMemory.title': 'Collection memory -- annual',
  'collectionMemory.subtitle': 'How our collection has accumulated over time.',
  'collectionMemory.loading': 'Loading...',
  'collectionMemory.empty': 'No rationale data yet.',
  'collectionMemory.colYear': 'Year',
  'collectionMemory.colUseCase': 'Use case',
  'collectionMemory.colWeeding': 'Weeding condition',
  'collectionMemory.colItems': 'Items',
  'collectionMemory.colAnticipated': 'Anticipated challenge',
  'collectionMemory.colPatronVisible': 'Patron-visible',
}

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      const raw = STRINGS[key] ?? key
      if (!params) return raw
      return Object.entries(params).reduce(
        (acc, [k, v]) => acc.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v)),
        raw,
      )
    },
  }),
}))

vi.mock('@/lib/api-client', () => ({
  api: {
    get: vi.fn().mockResolvedValue({
      rows: [
        {
          year_acquired: '2026-01-01',
          primary_use_case_slug: 'new_parent',
          weeding_condition: 'current_5yr',
          item_count: 5,
          anticipated_count: 0,
          patron_visible_count: 0,
        },
        {
          year_acquired: '2026-01-01',
          primary_use_case_slug: 'grief_loss',
          weeding_condition: 'foundational_indefinite',
          item_count: 2,
          anticipated_count: 1,
          patron_visible_count: 0,
        },
      ],
    }),
  },
  isApiError: () => false,
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('AdminCollectionMemoryPage', () => {
  it('renders the aggregated table', async () => {
    render(
      <MemoryRouter>
        <AdminCollectionMemoryPage />
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText(/new_parent/)).toBeInTheDocument())
    expect(screen.getByText(/grief_loss/)).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('renders heading from i18n', async () => {
    render(
      <MemoryRouter>
        <AdminCollectionMemoryPage />
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('heading', { name: /Collection memory -- annual/ }),
    ).toBeInTheDocument()
  })

  it('shows empty state when no rows returned', async () => {
    const mod = await import('@/lib/api-client')
    ;(mod.api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ rows: [] })
    render(
      <MemoryRouter>
        <AdminCollectionMemoryPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(/No rationale data yet/)).toBeInTheDocument()
    })
  })

  it('shows error when fetch fails', async () => {
    const mod = await import('@/lib/api-client')
    ;(mod.api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('boom'))
    render(
      <MemoryRouter>
        <AdminCollectionMemoryPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('boom')
    })
  })
})
