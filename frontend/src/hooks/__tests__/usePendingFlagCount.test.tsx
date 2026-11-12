/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { usePendingFlagCount } from '@/hooks/usePendingFlagCount'
import api from '@/api/api'

vi.mock('@/api/api')

beforeEach(() => { vi.clearAllMocks() })

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

it('returns the count of pending flags', async () => {
  ;(api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ data: [{ id: 1 }, { id: 2 }] })
  const { result } = renderHook(() => usePendingFlagCount(true), { wrapper: makeWrapper() })
  await waitFor(() => expect(result.current).toBe(2))
})

it('returns 0 when disabled', async () => {
  const { result } = renderHook(() => usePendingFlagCount(false), { wrapper: makeWrapper() })
  await waitFor(() => expect(result.current).toBe(0))
  expect((api.get as unknown as ReturnType<typeof vi.fn>)).not.toHaveBeenCalled()
})

it('returns 0 on fetch error', async () => {
  ;(api.get as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('network'))
  const { result } = renderHook(() => usePendingFlagCount(true), { wrapper: makeWrapper() })
  await waitFor(() => expect(result.current).toBe(0))
})
