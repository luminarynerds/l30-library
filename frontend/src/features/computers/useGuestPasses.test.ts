/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useGuestPasses } from './useGuestPasses'

vi.mock('@/lib/api-client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import api from '@/lib/api-client'

const mockedGet = api.get as unknown as ReturnType<typeof vi.fn>
const mockedPost = api.post as unknown as ReturnType<typeof vi.fn>

describe('useGuestPasses', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('list() fetches passes from the staff endpoint and stores them in state', async () => {
    const samplePasses = [
      { id: 1, guest_name: 'Jane', pass_code: 'ABC123' },
      { id: 2, guest_name: 'John', pass_code: 'XYZ789' },
    ]
    mockedGet.mockResolvedValueOnce({ items: samplePasses })

    const { result } = renderHook(() => useGuestPasses())

    await act(async () => {
      await result.current.list()
    })

    expect(mockedGet).toHaveBeenCalledTimes(1)
    expect(mockedGet.mock.calls[0]![0]).toMatch(/\/computers\/staff\/guest-passes$/)
    expect(result.current.passes).toEqual(samplePasses)
    expect(result.current.loading).toBe(false)
  })

  it('list() handles empty response by storing an empty array', async () => {
    mockedGet.mockResolvedValueOnce({})

    const { result } = renderHook(() => useGuestPasses())
    await act(async () => {
      await result.current.list()
    })

    expect(result.current.passes).toEqual([])
  })

  it('create() POSTs to /guest-passes and re-fetches passes', async () => {
    const created = { id: 3, guest_name: 'New', pass_code: 'NEW001' }
    mockedPost.mockResolvedValueOnce(created)
    mockedGet.mockResolvedValueOnce({ items: [created] })

    const { result } = renderHook(() => useGuestPasses())
    let returned: unknown
    await act(async () => {
      returned = await result.current.create({
        guest_name: 'New',
        max_sessions: 1,
        max_duration_minutes_per_session: 60,
      })
    })

    expect(mockedPost).toHaveBeenCalledTimes(1)
    expect(mockedPost.mock.calls[0]![0]).toMatch(/\/computers\/guest-passes$/)
    expect(mockedGet).toHaveBeenCalledTimes(1)
    expect(returned).toEqual(created)
    expect(result.current.passes).toEqual([created])
  })
})
