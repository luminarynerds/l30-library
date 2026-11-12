/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { I18nProvider } from '@/i18n/I18nContext'
import { UnifiedAccessibilityProvider } from '@/features/accessibility/context/UnifiedAccessibilityContext'
import { BrandingProvider } from '@/contexts/BrandingContext'
import { useCatalogSearch } from '@/pages/catalog/hooks/useCatalogSearch'

beforeEach(() => {
  localStorage.clear()
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(
      JSON.stringify({ items: [], total: 0, pages: 1, results: [], total_results: 0 }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    ),
  )
})

function makeWrapper(initialUrl: string) {
  const url = new URL('http://localhost' + initialUrl)
  Object.defineProperty(window, 'location', {
    value: { ...window.location, search: url.search, pathname: url.pathname },
    writable: true,
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    return (
      <QueryClientProvider client={client}>
        <BrandingProvider>
          <I18nProvider>
            <UnifiedAccessibilityProvider>
              <MemoryRouter initialEntries={[initialUrl]}>{children}</MemoryRouter>
            </UnifiedAccessibilityProvider>
          </I18nProvider>
        </BrandingProvider>
      </QueryClientProvider>
    )
  }
}

describe('useCatalogSearch -- author_facets plumbing', () => {
  it('hydrates author_facets from URL repeated params', () => {
    const { result } = renderHook(() => useCatalogSearch(), {
      wrapper: makeWrapper('/catalog?author_facets=Spiegelman&author_facets=Satrapi'),
    })
    expect(result.current.filters.author_facets).toEqual(['Spiegelman', 'Satrapi'])
  })

  it('builds author chips and chip removal leaves the rest', () => {
    const { result } = renderHook(() => useCatalogSearch(), {
      wrapper: makeWrapper('/catalog?author_facets=Spiegelman&author_facets=Satrapi'),
    })
    const chipKeys = result.current.activeFilterChips.map(c => c.key)
    expect(chipKeys).toContain('author_facets:Spiegelman')
    expect(chipKeys).toContain('author_facets:Satrapi')

    act(() => {
      result.current.handleRemoveChip('author_facets:Spiegelman', 'Author: Spiegelman')
    })
    expect(result.current.filters.author_facets).toEqual(['Satrapi'])
  })

  it('caps incoming URL at 20 entries', () => {
    const params = Array.from({ length: 25 }, (_, i) => `author_facets=A${i}`).join('&')
    const { result } = renderHook(() => useCatalogSearch(), {
      wrapper: makeWrapper(`/catalog?${params}`),
    })
    expect(result.current.filters.author_facets).toHaveLength(20)
  })

  it('onAuthorFacetsChange replaces array and caps at 20', () => {
    const { result } = renderHook(() => useCatalogSearch(), {
      wrapper: makeWrapper('/catalog'),
    })
    act(() => {
      result.current.onAuthorFacetsChange(['A', 'B', 'C'])
    })
    expect(result.current.filters.author_facets).toEqual(['A', 'B', 'C'])

    const big = Array.from({ length: 30 }, (_, i) => `A${i}`)
    act(() => {
      result.current.onAuthorFacetsChange(big)
    })
    expect(result.current.filters.author_facets).toHaveLength(20)
  })
})

describe('useCatalogSearch -- series_facets plumbing', () => {
  it('hydrates series_facets from URL repeated params', () => {
    const { result } = renderHook(() => useCatalogSearch(), {
      wrapper: makeWrapper('/catalog?series_facets=Maus&series_facets=Persepolis'),
    })
    expect(result.current.filters.series_facets).toEqual(['Maus', 'Persepolis'])
  })

  it('builds series chips and chip removal leaves the rest', () => {
    const { result } = renderHook(() => useCatalogSearch(), {
      wrapper: makeWrapper('/catalog?series_facets=Maus&series_facets=Persepolis'),
    })
    const chipKeys = result.current.activeFilterChips.map(c => c.key)
    expect(chipKeys).toContain('series_facets:Maus')
    expect(chipKeys).toContain('series_facets:Persepolis')

    act(() => {
      result.current.handleRemoveChip('series_facets:Maus', 'Series: Maus')
    })
    expect(result.current.filters.series_facets).toEqual(['Persepolis'])
  })

  it('caps incoming URL at 20 entries', () => {
    const params = Array.from({ length: 25 }, (_, i) => `series_facets=S${i}`).join('&')
    const { result } = renderHook(() => useCatalogSearch(), {
      wrapper: makeWrapper(`/catalog?${params}`),
    })
    expect(result.current.filters.series_facets).toHaveLength(20)
  })

  it('onSeriesFacetsChange replaces array and caps at 20', () => {
    const { result } = renderHook(() => useCatalogSearch(), {
      wrapper: makeWrapper('/catalog'),
    })
    act(() => {
      result.current.onSeriesFacetsChange(['A', 'B', 'C'])
    })
    expect(result.current.filters.series_facets).toEqual(['A', 'B', 'C'])

    const big = Array.from({ length: 30 }, (_, i) => `S${i}`)
    act(() => {
      result.current.onSeriesFacetsChange(big)
    })
    expect(result.current.filters.series_facets).toHaveLength(20)
  })
})
