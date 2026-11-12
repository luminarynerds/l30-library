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

// Stub fetch so the useQuery inside the hook doesn't try to hit a real endpoint.
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
  // Set window.location.search so the hook's initialParams ref picks it up.
  // (The hook reads window.location.search directly, not just MemoryRouter state.)
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

describe('useCatalogSearch -- subject_facets plumbing', () => {
  it('hydrates subject_facets from URL repeated params', () => {
    const { result } = renderHook(() => useCatalogSearch(), {
      wrapper: makeWrapper('/catalog?subject_facets=Fiction&subject_facets=History'),
    })
    expect(result.current.filters.subject_facets).toEqual(['Fiction', 'History'])
  })

  it('builds subject_facets chips and chip removal leaves the rest', () => {
    const { result } = renderHook(() => useCatalogSearch(), {
      wrapper: makeWrapper('/catalog?subject_facets=Fiction&subject_facets=History'),
    })
    // Verify chips include subject_facets:Fiction
    const chipKeys = result.current.activeFilterChips.map(c => c.key)
    expect(chipKeys).toContain('subject_facets:Fiction')
    expect(chipKeys).toContain('subject_facets:History')

    act(() => {
      result.current.handleRemoveChip('subject_facets:Fiction', 'Subject: Fiction')
    })
    expect(result.current.filters.subject_facets).toEqual(['History'])
  })

  it('caps incoming URL at 20 entries (DoS guard parity with backend)', () => {
    const params = Array.from({ length: 25 }, (_, i) => `subject_facets=S${i}`).join('&')
    const { result } = renderHook(() => useCatalogSearch(), {
      wrapper: makeWrapper(`/catalog?${params}`),
    })
    expect(result.current.filters.subject_facets).toHaveLength(20)
  })

  it('onSubjectFacetsChange replaces array and caps at 20', () => {
    const { result } = renderHook(() => useCatalogSearch(), {
      wrapper: makeWrapper('/catalog'),
    })
    act(() => {
      result.current.onSubjectFacetsChange(['A', 'B', 'C'])
    })
    expect(result.current.filters.subject_facets).toEqual(['A', 'B', 'C'])

    const big = Array.from({ length: 30 }, (_, i) => `S${i}`)
    act(() => {
      result.current.onSubjectFacetsChange(big)
    })
    expect(result.current.filters.subject_facets).toHaveLength(20)
  })
})
