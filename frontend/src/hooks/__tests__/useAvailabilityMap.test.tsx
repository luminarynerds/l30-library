/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

vi.mock('@/lib/api-client', () => ({ fetchApi: vi.fn() }))

import { fetchApi } from '@/lib/api-client'
import { useAvailabilityMap, type ItemAvailabilityInfo } from '../useAvailabilityMap'

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

const info = (item_id: number, total: number, available: number): ItemAvailabilityInfo => ({
  item_id,
  total_copies: total,
  available_copies: available,
  on_loan: total - available,
  status: available > 1 ? 'available' : available === 1 ? 'limited' : 'unavailable',
  next_available_date: null,
})

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useAvailabilityMap', () => {
  it('does not fetch when there are no item ids', async () => {
    const { result } = renderHook(() => useAvailabilityMap([]), { wrapper })
    expect(result.current.size).toBe(0)
    expect(fetchApi).not.toHaveBeenCalled()
  })

  it('makes a single batched POST for the page and returns a map by item id', async () => {
    vi.mocked(fetchApi).mockResolvedValue([info(1, 3, 2), info(2, 1, 0)])

    const { result } = renderHook(() => useAvailabilityMap([2, 1, 2]), { wrapper })

    await waitFor(() => expect(result.current.size).toBe(2))
    expect(fetchApi).toHaveBeenCalledTimes(1)
    // ids deduped and sorted for a stable cache key
    expect(fetchApi).toHaveBeenCalledWith('/catalog/batch-availability', {
      method: 'POST',
      body: { item_ids: [1, 2] },
    })
    expect(result.current.get(1)).toMatchObject({ total_copies: 3, available_copies: 2 })
    expect(result.current.get(2)).toMatchObject({ total_copies: 1, available_copies: 0 })
  })

  it('caps the batch at 50 ids (backend limit)', async () => {
    vi.mocked(fetchApi).mockResolvedValue([])
    const ids = Array.from({ length: 60 }, (_, i) => i + 1)

    renderHook(() => useAvailabilityMap(ids), { wrapper })

    await waitFor(() => expect(fetchApi).toHaveBeenCalledTimes(1))
    const body = vi.mocked(fetchApi).mock.calls[0]![1] as { body: { item_ids: number[] } }
    expect(body.body.item_ids).toHaveLength(50)
  })

  it('returns an empty map on fetch failure', async () => {
    vi.mocked(fetchApi).mockRejectedValue(new Error('boom'))

    const { result } = renderHook(() => useAvailabilityMap([1]), { wrapper })

    await waitFor(() => expect(fetchApi).toHaveBeenCalled())
    expect(result.current.size).toBe(0)
  })
})
