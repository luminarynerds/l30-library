/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EbookActionPanel from '../EbookActionPanel'
import { getActiveBorrows, type IndieEbookPublic, type EbookBorrow } from '@/api/indie-catalog-api'

// A logged-in patron (the real getPatronType() is a stub that returns 'anonymous').
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: '667', email: 'demo.patron@l30.org', role: 'PATRON' } }),
}))

// Key-returning translation stub so we can assert on i18n keys.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}))

// Keep the real module (getPatronType/getBuyNowStatus stay harmless stubs that
// reject in the test fetch) but make getActiveBorrows controllable so we can
// exercise the borrowed-state CTA.
vi.mock('@/api/indie-catalog-api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/indie-catalog-api')>()
  return { ...actual, getActiveBorrows: vi.fn() }
})

const mockGetActiveBorrows = vi.mocked(getActiveBorrows)

const availableBook = {
  id: 50,
  indie_ebook_id: 18,
  title: 'Ember and Thorn',
  available_copies: 2,
  total_copies: 3,
  borrow_duration_days: 21,
  catalog_item_id: null,
} as unknown as IndieEbookPublic

function makeBorrow(overrides: Partial<EbookBorrow> = {}): EbookBorrow {
  return {
    id: 9,
    ebook_id: 50,
    indie_ebook_id: 18,
    ebook_title: 'Ember and Thorn',
    ebook_cover_url: null,
    author_pen_name: 'A. Author',
    borrowed_at: new Date(Date.now() - 86_400_000).toISOString(),
    due_at: new Date(Date.now() + 10 * 86_400_000).toISOString(),
    status: 'active',
    download_count: 0,
    max_downloads: 5,
    renewal_count: 0,
    can_renew: true,
    ...overrides,
  } as EbookBorrow
}

function renderPanel(book: IndieEbookPublic = availableBook) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EbookActionPanel book={book} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  mockGetActiveBorrows.mockReset()
})

describe('EbookActionPanel — logged-in patron borrow CTA', () => {
  it('shows a Borrow button (not a sign-in link) for a logged-in patron on an available title', async () => {
    // Regression: getPatronType() returns a hardcoded 'anonymous', which used to
    // resolve every logged-in patron to the anonymous branch and render
    // "Sign in to Borrow" -> /login -> /account, so borrowing was impossible.
    mockGetActiveBorrows.mockResolvedValue([])
    renderPanel()
    const borrowBtn = await screen.findByRole('button', { name: /indieBookDetail\.borrowFor/i })
    expect(borrowBtn).toBeTruthy()
    expect(screen.queryByRole('link', { name: /indieBookDetail\.signInToBorrow/i })).toBeNull()
  })

  it('shows Read now + Return + due date (and hides Borrow) when the patron already has this title out', async () => {
    // The borrowed-state branch keys on the IndieEbook PK (indie_ebook_id), the
    // universal lending key — matched against the active-borrows list.
    mockGetActiveBorrows.mockResolvedValue([makeBorrow()])
    renderPanel()
    // The link's accessible name is its aria-label ("Read {title} in your
    // browser"), added in the same commit as this test (5e0c343c3) for a11y —
    // it overrides the visible "Read now" text as the accessible name.
    expect(await screen.findByRole('link', { name: /Read Ember and Thorn in your browser/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Return Ember and Thorn/i })).toBeTruthy()
    expect(screen.getByText(/Due in 10 days/i)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /indieBookDetail\.borrowFor/i })).toBeNull()
  })

  it('keeps the Borrow CTA when the only active borrow is a different title', async () => {
    // Guards against matching on the wrong id space (PK 18 vs MetisLib id 50).
    mockGetActiveBorrows.mockResolvedValue([makeBorrow({ indie_ebook_id: 999, ebook_id: 999 })])
    renderPanel()
    expect(await screen.findByRole('button', { name: /indieBookDetail\.borrowFor/i })).toBeTruthy()
    expect(screen.queryByRole('link', { name: /Read now/i })).toBeNull()
  })
})
