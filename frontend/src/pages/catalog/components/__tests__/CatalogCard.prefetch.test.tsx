/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Hover/focus prefetch of item-detail React Query — Fix 4 from the
 * 2026-05-16 audit (perf enhancement bundle).
 */
import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CatalogListCard from '../CatalogListCard'
import CatalogGridCard from '../CatalogGridCard'
import type { CatalogItem } from '@/api/api'

vi.mock('@/components/shelf/ShelfBookmark', () => ({ default: () => null }))
vi.mock('@/components/reading-lists/AddToListDropdown', () => ({
  AddToListDropdown: () => null,
}))
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: null, token: null }),
}))
vi.mock('../PlaceHoldModal', () => ({ PlaceHoldModal: () => null }))
vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    language: 'en-US',
    t: (key: string, fb?: unknown) => (typeof fb === 'string' ? fb : key),
  }),
}))

// Spy on the API the prefetch should call.
const getCatalogItemSpy = vi.fn().mockResolvedValue({ id: 99, title: 'X' })
vi.mock('@/api/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/api')>()
  return {
    ...actual,
    getCatalogItem: (...args: unknown[]) => getCatalogItemSpy(...args),
  }
})

const baseItem: CatalogItem = {
  id: 99,
  title: 'Prefetch Test',
  author: 'A',
  item_type: 'book',
  status: 'available',
  isbn: '978',
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

function makeProviders() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const prefetchSpy = vi.spyOn(qc, 'prefetchQuery')
  const Wrap = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
  return { Wrap, prefetchSpy }
}

describe('Fix 4: list card prefetches item detail on hover and focus', () => {
  it('calls queryClient.prefetchQuery with the catalog-item key on mouseEnter', () => {
    const { Wrap, prefetchSpy } = makeProviders()
    const { container } = render(
      <Wrap>
        <CatalogListCard
          item={baseItem}
          simplifiedView={false}
          quietMode={false}
          showImages={true}
          isSpeaking={false}
          onSpeak={vi.fn()}
          onStopSpeak={vi.fn()}
        />
      </Wrap>,
    )
    const link = container.querySelector('a')!
    fireEvent.mouseEnter(link)
    expect(prefetchSpy).toHaveBeenCalled()
    const call = prefetchSpy.mock.calls[0]![0] as {
      queryKey: unknown
      staleTime: number
    }
    expect(call.queryKey).toEqual(['catalog-item', 99])
    expect(call.staleTime).toBe(5 * 60 * 1000)
  })

  it('also prefetches on focus', () => {
    const { Wrap, prefetchSpy } = makeProviders()
    const { container } = render(
      <Wrap>
        <CatalogListCard
          item={baseItem}
          simplifiedView={false}
          quietMode={false}
          showImages={true}
          isSpeaking={false}
          onSpeak={vi.fn()}
          onStopSpeak={vi.fn()}
        />
      </Wrap>,
    )
    const link = container.querySelector('a')!
    fireEvent.focus(link)
    expect(prefetchSpy).toHaveBeenCalled()
  })
})

describe('Fix 4: grid card prefetches item detail on hover and focus', () => {
  it('prefetches on mouseEnter', () => {
    const { Wrap, prefetchSpy } = makeProviders()
    const { container } = render(
      <Wrap>
        <CatalogGridCard item={baseItem} />
      </Wrap>,
    )
    fireEvent.mouseEnter(container.querySelector('a')!)
    expect(prefetchSpy).toHaveBeenCalled()
    const call = prefetchSpy.mock.calls[0]![0] as { queryKey: unknown }
    expect(call.queryKey).toEqual(['catalog-item', 99])
  })

  it('prefetches on focus', () => {
    const { Wrap, prefetchSpy } = makeProviders()
    const { container } = render(
      <Wrap>
        <CatalogGridCard item={baseItem} />
      </Wrap>,
    )
    fireEvent.focus(container.querySelector('a')!)
    expect(prefetchSpy).toHaveBeenCalled()
  })
})
