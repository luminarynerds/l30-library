/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Contract test for the React Query v5 `placeholderData: keepPreviousData`
 * option used by `useCatalogSearch`. We don't render the full hook (it has
 * 14+ dependencies); instead we prove the option's user-visible behavior:
 * when the queryKey changes, `data` retains the previous value while
 * `isFetching` is true — i.e., the catalog results stay on-screen during
 * filter refinements rather than blanking to skeletons.
 */
import React from 'react'
import { describe, it, expect } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  keepPreviousData,
} from '@tanstack/react-query'

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

describe('placeholderData: keepPreviousData (React Query v5 contract)', () => {
  it('keeps previous data visible while the next query is fetching', async () => {
    let resolveSecond: ((v: string) => void) | undefined

    const { result, rerender } = renderHook(
      ({ key }: { key: string }) =>
        useQuery({
          queryKey: ['catalog-unified-test', key],
          queryFn: () =>
            key === 'first'
              ? Promise.resolve('first-results')
              : new Promise<string>((resolve) => {
                  resolveSecond = resolve
                }),
          placeholderData: keepPreviousData,
        }),
      { wrapper: makeWrapper(), initialProps: { key: 'first' } },
    )

    // Wait for the first fetch to settle.
    await waitFor(() => expect(result.current.data).toBe('first-results'))
    expect(result.current.isFetching).toBe(false)

    // Trigger a new query by changing the key — DO NOT resolve the new fetch yet.
    rerender({ key: 'second' })

    // While in flight, `data` MUST still equal the previous result.
    await waitFor(() => expect(result.current.isFetching).toBe(true))
    expect(result.current.data).toBe('first-results')
    expect(result.current.isPlaceholderData).toBe(true)
    // `isLoading` is false because we have placeholder data — this is what
    // keeps the skeleton from rendering in CatalogResultsList.
    expect(result.current.isLoading).toBe(false)

    // Resolve the second fetch — data should advance.
    await act(async () => {
      resolveSecond?.('second-results')
    })
    await waitFor(() => expect(result.current.data).toBe('second-results'))
    expect(result.current.isPlaceholderData).toBe(false)
  })
})
