/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (_key: string, fallbackOrParams?: unknown) =>
      typeof fallbackOrParams === 'string' ? fallbackOrParams : _key,
    language: 'en' as const,
    setLanguage: () => undefined,
    isRTL: false,
  }),
  I18nProvider: ({ children }: { children: React.ReactNode }) => children,
}))

vi.mock('@/i18n', () => ({
  t: (key: string) => key,
}))

import CatalogResultsList from '../CatalogResultsList'
import { CatalogItemSkeleton } from '@/components/skeletons/CatalogItemSkeleton'

function renderResults(
  overrides: Partial<React.ComponentProps<typeof CatalogResultsList>> = {},
) {
  const props: React.ComponentProps<typeof CatalogResultsList> = {
    filteredItems: [],
    viewMode: 'list',
    isLoading: true,
    error: null,
    data: undefined,
    activeQuery: '',
    hasActiveFilters: false,
    effectiveQuietMode: false,
    effectiveSimplifiedView: false,
    effectiveShowImages: true,
    speakingItemId: null,
    onSpeak: vi.fn(),
    onStopSpeak: vi.fn(),
    shouldVirtualize: false,
    virtualizer: {} as never,
    virtualScrollRef: { current: null },
    preferPagination: false,
    currentPage: 1,
    onPageChange: vi.fn(),
    didYouMean: null,
    onDidYouMeanClick: vi.fn(),
    onClearFilters: vi.fn(),
    onBrowseFormat: vi.fn(),
    shelfStatusMap: new Map(),
    languageFilter: '',
    ...overrides,
  }
  return render(
    <MemoryRouter>
      <CatalogResultsList {...props} />
    </MemoryRouter>,
  )
}

function countSkeletons(container: HTMLElement): number {
  // Each skeleton item carries role=status with the loading aria label.
  // Exclude the empty-state status region which only renders when !isLoading.
  return container.querySelectorAll('[role="status"]').length
}

describe('CatalogResultsList skeleton count parity', () => {
  it('renders default 5 list skeletons when data is undefined', () => {
    const { container } = renderResults({ viewMode: 'list', data: undefined })
    expect(countSkeletons(container)).toBe(5)
  })

  it('renders default 8 grid skeletons when data is undefined', () => {
    const { container } = renderResults({ viewMode: 'grid', data: undefined })
    expect(countSkeletons(container)).toBe(8)
  })

  it('renders 13 list skeletons when previous data.total is 13', () => {
    const { container } = renderResults({
      viewMode: 'list',
      data: { total: 13, pages: 1, per_page: 20 } as never,
    })
    expect(countSkeletons(container)).toBe(13)
  })

  it('renders 13 grid skeletons when previous data.total is 13', () => {
    const { container } = renderResults({
      viewMode: 'grid',
      data: { total: 13, pages: 1, per_page: 20 } as never,
    })
    expect(countSkeletons(container)).toBe(13)
  })

  it('caps skeleton count at data.per_page when total exceeds it', () => {
    const { container } = renderResults({
      viewMode: 'list',
      data: { total: 5000, pages: 250, per_page: 20 } as never,
    })
    expect(countSkeletons(container)).toBe(20)
  })
})

describe('CatalogItemSkeleton list-card height parity', () => {
  it('list skeleton uses p-5 to match real CatalogListCard padding', () => {
    const { container } = render(<CatalogItemSkeleton />)
    const root = container.firstChild as HTMLElement
    expect(root.className).toContain('p-5')
  })

  it('list skeleton cover uses h-[120px] to match real cover height', () => {
    const { container } = render(<CatalogItemSkeleton />)
    // First inner div is the cover placeholder.
    const cover = container.querySelector('.flex.gap-4 > div') as HTMLElement | null
    expect(cover).not.toBeNull()
    expect(cover!.className).toContain('h-[120px]')
    expect(cover!.className).toContain('w-20')
  })
})
