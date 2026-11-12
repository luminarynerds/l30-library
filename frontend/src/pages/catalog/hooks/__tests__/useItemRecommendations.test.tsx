/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Read-alikes hook: sorts available-first (preserving backend pin/rank
 * order within each group), returns an empty list on fetch failure, and
 * never fires without an item id.
 */
import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useItemRecommendations } from '../useItemRecommendations'
import type { ItemRecommendationsResponse } from '@/api/api'

vi.mock('@/api/api', async () => {
  const actual = await vi.importActual<object>('@/api/api')
  return { ...actual, getItemRecommendations: vi.fn() }
})
import { getItemRecommendations } from '@/api/api'

function makeResponse(items: Array<{ id: number; available: boolean }>): ItemRecommendationsResponse {
  return {
    items: items.map(({ id, available }) => ({
      id,
      title: `Title ${id}`,
      author: `Author ${id}`,
      is_pinned: false,
      cover_image: null,
      available,
    })),
    total_pinned: 0,
    algorithm_used: 'semantic',
  }
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useItemRecommendations', () => {
  beforeEach(() => {
    vi.mocked(getItemRecommendations).mockReset()
  })

  it('sorts available items first, preserving backend order within groups', async () => {
    vi.mocked(getItemRecommendations).mockResolvedValue(
      makeResponse([
        { id: 1, available: false },
        { id: 2, available: true },
        { id: 3, available: false },
        { id: 4, available: true },
      ])
    )

    const { result } = renderHook(() => useItemRecommendations(42), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.items).toHaveLength(4))
    expect(result.current.items.map((i) => i.id)).toEqual([2, 4, 1, 3])
    expect(getItemRecommendations).toHaveBeenCalledWith(42)
  })

  it('returns an empty list when the fetch fails', async () => {
    vi.mocked(getItemRecommendations).mockRejectedValue(new Error('boom'))

    const { result } = renderHook(() => useItemRecommendations(42), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.items).toEqual([])
  })

  it('does not fetch when id is undefined', () => {
    const { result } = renderHook(() => useItemRecommendations(undefined), {
      wrapper: createWrapper(),
    })

    expect(getItemRecommendations).not.toHaveBeenCalled()
    expect(result.current.items).toEqual([])
  })
})
