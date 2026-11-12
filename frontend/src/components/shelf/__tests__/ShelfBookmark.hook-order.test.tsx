/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Regression: ShelfBookmark hook order across feature-flag flips.
 *
 * The reading_shelf_enabled flag hydrates from false to true once the
 * organization features query settles. Pre-fix the component returned null
 * before reaching three later hooks (useState for isMobile, useEffect for
 * matchMedia, useCallback for handleClick), so when the flag flipped the
 * hook count changed and React threw #310 "Rendered more hooks than during
 * the previous render" — caught silently by the patron catalog error
 * boundary on /catalog and /catalog/mood/* until PR #1045.
 *
 * This test re-renders the component with the feature flag flipping from
 * false to true and asserts no throw.
 */
import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Mutable refs so the mocked hooks can swap return values mid-test.
const featureFlagRef = { value: false }

vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({
    isFeatureEnabled: (_: string) => featureFlagRef.value,
  }),
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: null, token: null }),
}))

vi.mock('@/hooks/useReadingStatus', () => ({
  useReadingStatus: () => ({
    handleSetStatus: vi.fn(),
    handleRemove: vi.fn(),
    isUpdating: false,
  }),
}))

vi.mock('@/hooks/useShelfStatusMap', () => ({
  useShelfStatusMap: () => new Map<number, string>(),
  SHELF_TOP_BORDER_COLORS: {},
  SHELF_STATUS_LABELS: {},
}))

vi.mock('@/features/accessibility/hooks/useUnifiedAccessibility', () => ({
  useUnifiedAccessibility: () => ({ announceToScreenReader: vi.fn() }),
}))

import ShelfBookmark from '@/components/shelf/ShelfBookmark'

function renderWith(props: { catalogItemId: number }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ShelfBookmark {...props} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ShelfBookmark hook order', () => {
  it('does not throw when reading_shelf_enabled flips false -> true mid-mount', () => {
    featureFlagRef.value = false
    const { rerender, container } = renderWith({ catalogItemId: 1 })

    // First render: flag false, component returns null. No bookmark in DOM.
    expect(container.querySelector('button[aria-label]')).toBeNull()

    // Flag flips to true; React re-renders. Pre-fix, the hook count grew
    // from 7 to 10 here and React threw #310.
    featureFlagRef.value = true
    expect(() =>
      rerender(
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
          <MemoryRouter>
            <ShelfBookmark catalogItemId={1} />
          </MemoryRouter>
        </QueryClientProvider>,
      ),
    ).not.toThrow()
  })

  it('does not throw when reading_shelf_enabled flips true -> false mid-mount', () => {
    featureFlagRef.value = true
    const { rerender } = renderWith({ catalogItemId: 2 })

    featureFlagRef.value = false
    expect(() =>
      rerender(
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
          <MemoryRouter>
            <ShelfBookmark catalogItemId={2} />
          </MemoryRouter>
        </QueryClientProvider>,
      ),
    ).not.toThrow()
  })
})
