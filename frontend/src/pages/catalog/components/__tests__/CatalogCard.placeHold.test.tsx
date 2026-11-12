/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Inline Place Hold CTA on result cards — Fix 3 from the 2026-05-16 audit.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CatalogListCard from '../CatalogListCard'
import CatalogGridCard from '../CatalogGridCard'
import type { CatalogItem } from '@/api/api'

vi.mock('@/components/shelf/ShelfBookmark', () => ({ default: () => null }))
vi.mock('@/components/reading-lists/AddToListDropdown', () => ({
  AddToListDropdown: () => null,
}))

// Hoisted auth mock so we can flip user state between tests.
const auth = vi.hoisted(() => ({ value: { user: { id: 1 }, token: 't' } as { user: unknown; token: string | null } }))
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => auth.value,
}))

// Stub the modal so we assert "opened" without exercising its internals.
vi.mock('../PlaceHoldModal', () => ({
  PlaceHoldModal: ({ item, onClose }: { item: CatalogItem; onClose: () => void }) => (
    <div data-testid="hold-modal-stub" data-item-id={item.id}>
      {/* A non-dismissing region whose click must NOT bubble to the card's
          <Link> and trigger navigation (the real bug). */}
      <p data-testid="hold-modal-body">modal for {item.title}</p>
      <button onClick={onClose}>close</button>
    </div>
  ),
}))

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    language: 'en-US',
    t: (key: string, paramsOrFallback?: unknown) =>
      typeof paramsOrFallback === 'string' ? paramsOrFallback : key,
  }),
}))

const baseItem: CatalogItem = {
  id: 33,
  title: 'Test Holdable',
  author: 'Test Author',
  item_type: 'book',
  status: 'checked_out',
  isbn: '978-0',
  publisher: 'P',
  publication_year: 2024,
  description: null,
  subjects: null,
  cover_url: null,
  page_count: null,
  location: null,
  barcode: '1',
  created_at: '2024-01-01T00:00:00Z',
} as unknown as CatalogItem

/** Surfaces the active route so tests can assert (no) navigation. */
function LocationProbe() {
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from
  return (
    <>
      <div data-testid="location">{location.pathname}</div>
      <div data-testid="location-state-from">{from ?? ''}</div>
    </>
  )
}

function withProviders(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        {ui}
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function renderList(item: CatalogItem = baseItem) {
  return render(
    withProviders(
      <CatalogListCard
        item={item}
        simplifiedView={false}
        quietMode={false}
        showImages={true}
        isSpeaking={false}
        onSpeak={vi.fn()}
        onStopSpeak={vi.fn()}
      />,
    ),
  )
}

function renderGrid(item: CatalogItem = baseItem) {
  return render(withProviders(<CatalogGridCard item={item} />))
}

beforeEach(() => {
  auth.value = { user: { id: 1 }, token: 't' }
})

describe('Fix 3: Place Hold button on list card', () => {
  it('renders for authenticated user on a holdable item', () => {
    renderList()
    const btn = screen.getByRole('button', { name: /hold/i })
    expect(btn).toBeTruthy()
  })

  it('opens the PlaceHoldModal on click without navigating', () => {
    renderList()
    const btn = screen.getByRole('button', { name: /hold/i })
    // Wrap in act-equivalent via fireEvent; assert default is prevented by
    // confirming clicking does not throw and the modal is in the DOM.
    fireEvent.click(btn)
    expect(screen.getByTestId('hold-modal-stub')).toBeTruthy()
    expect(screen.getByTestId('hold-modal-stub').getAttribute('data-item-id')).toBe('33')
  })

  it('shows a sign-in CTA for unauthenticated users that routes to login with a return target', () => {
    auth.value = { user: null, token: null }
    renderList()
    expect(screen.queryByRole('button', { name: /^place hold/i })).toBeNull()
    const btn = screen.getByRole('button', { name: /sign in to place hold/i })
    fireEvent.click(btn)
    expect(screen.getByTestId('location').textContent).toBe('/login')
    expect(screen.getByTestId('location-state-from').textContent).toBe('/catalog/33?action=hold')
    // Modal must not open for logged-out users.
    expect(screen.queryByTestId('hold-modal-stub')).toBeNull()
  })

  it('shows no hold CTA at all for unauthenticated users on non-holdable items', () => {
    auth.value = { user: null, token: null }
    renderList({ ...baseItem, status: 'withdrawn' } as CatalogItem)
    expect(screen.queryByRole('button', { name: /hold/i })).toBeNull()
  })

  it('is hidden for non-holdable terminal statuses', () => {
    renderList({ ...baseItem, status: 'withdrawn' } as CatalogItem)
    expect(screen.queryByRole('button', { name: /hold/i })).toBeNull()
  })

  it('does not navigate when clicking inside the opened modal', () => {
    renderList()
    expect(screen.getByTestId('location').textContent).toBe('/')
    fireEvent.click(screen.getByRole('button', { name: /hold/i }))
    // Clicking modal content must not bubble to the card's <Link> and route
    // away to the item detail page.
    fireEvent.click(screen.getByTestId('hold-modal-body'))
    expect(screen.getByTestId('location').textContent).toBe('/')
  })
})

describe('Fix 3: Place Hold button on grid card', () => {
  it('renders for authenticated user on a holdable item', () => {
    renderGrid()
    expect(screen.getByRole('button', { name: /hold/i })).toBeTruthy()
  })

  it('opens the modal on click', () => {
    renderGrid()
    fireEvent.click(screen.getByRole('button', { name: /hold/i }))
    expect(screen.getByTestId('hold-modal-stub')).toBeTruthy()
  })

  it('shows a sign-in CTA for unauthenticated users that routes to login with a return target', () => {
    auth.value = { user: null, token: null }
    renderGrid()
    expect(screen.queryByRole('button', { name: /^place hold/i })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /sign in to place hold/i }))
    expect(screen.getByTestId('location').textContent).toBe('/login')
    expect(screen.getByTestId('location-state-from').textContent).toBe('/catalog/33?action=hold')
    expect(screen.queryByTestId('hold-modal-stub')).toBeNull()
  })

  it('does not navigate when clicking inside the opened modal', () => {
    renderGrid()
    expect(screen.getByTestId('location').textContent).toBe('/')
    fireEvent.click(screen.getByRole('button', { name: /hold/i }))
    fireEvent.click(screen.getByTestId('hold-modal-body'))
    expect(screen.getByTestId('location').textContent).toBe('/')
  })
})
