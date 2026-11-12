/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'

vi.mock('@/contexts/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('@/lib/api-client', () => ({ apiClient: vi.fn() }))

import { useAuth } from '@/contexts/AuthContext'
import { apiClient } from '@/lib/api-client'
import { useAllHubFavorites } from '../useAllHubFavorites'

beforeEach(() => { vi.clearAllMocks() })

describe('useAllHubFavorites', () => {
  it('returns empty and does not fetch when unauthenticated', async () => {
    vi.mocked(useAuth).mockReturnValue({ isAuthenticated: false } as any)
    const { result } = renderHook(() => useAllHubFavorites())
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.favoritePaths).toEqual([])
    expect(apiClient).not.toHaveBeenCalled()
  })

  it('fetches all hub favorites and dedups item paths preserving order', async () => {
    vi.mocked(useAuth).mockReturnValue({ isAuthenticated: true } as any)
    vi.mocked(apiClient).mockResolvedValue([
      { id: '1', hub_slug: 'collection', item_path: '/staff/cataloging', created_at: 'a' },
      { id: '2', hub_slug: 'front-desk', item_path: '/staff/patrons', created_at: 'b' },
      { id: '3', hub_slug: 'library', item_path: '/staff/cataloging', created_at: 'c' },
    ] as any)
    const { result } = renderHook(() => useAllHubFavorites())
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.favoritePaths).toEqual(['/staff/cataloging', '/staff/patrons'])
    expect(apiClient).toHaveBeenCalledWith('/hub-favorites', { method: 'GET' })
  })

  it('swallows fetch errors and returns empty', async () => {
    vi.mocked(useAuth).mockReturnValue({ isAuthenticated: true } as any)
    vi.mocked(apiClient).mockRejectedValue(new Error('boom'))
    const { result } = renderHook(() => useAllHubFavorites())
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.favoritePaths).toEqual([])
  })

  it('refetches when the staff-favorites-changed event fires', async () => {
    vi.mocked(useAuth).mockReturnValue({ isAuthenticated: true } as any)
    vi.mocked(apiClient)
      .mockResolvedValueOnce([] as any)
      .mockResolvedValueOnce([
        { id: '1', hub_slug: 'collection', item_path: '/staff/cataloging', created_at: 'a' },
      ] as any)
    const { result } = renderHook(() => useAllHubFavorites())
    await waitFor(() => expect(result.current.favoritePaths).toEqual([]))
    act(() => { window.dispatchEvent(new Event('staff-favorites-changed')) })
    await waitFor(() => expect(result.current.favoritePaths).toEqual(['/staff/cataloging']))
    expect(apiClient).toHaveBeenCalledTimes(2)
  })
})
