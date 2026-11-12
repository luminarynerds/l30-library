/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getAccessTokenMock, fetchApiMock } = vi.hoisted(() => ({
  getAccessTokenMock: vi.fn(),
  fetchApiMock: vi.fn(),
}))

vi.mock('@/utils/tokenStore', () => ({
  getAccessToken: getAccessTokenMock,
}))

vi.mock('@/lib/api-client', () => ({
  fetchApi: fetchApiMock,
  isApiError: (error: unknown) => Boolean(error && typeof error === 'object' && 'status' in (error as Record<string, unknown>)),
}))

import { getRecentSearches, unifiedSearch } from '@/api/staff-search-api'

describe('staff-search-api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not make unified search network calls when no token exists', async () => {
    getAccessTokenMock.mockReturnValue(null)

    const result = await unifiedSearch('alice')

    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error).toBe('Authentication required')
    }
    expect(fetchApiMock).not.toHaveBeenCalled()
  })

  it('does not make recent search network calls when no token exists', async () => {
    getAccessTokenMock.mockReturnValue(null)

    const result = await getRecentSearches(5)

    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error).toBe('Authentication required')
    }
    expect(fetchApiMock).not.toHaveBeenCalled()
  })

  it('uses fetchApi with auth token when available', async () => {
    getAccessTokenMock.mockReturnValue('token-123')
    fetchApiMock.mockResolvedValueOnce({ searches: ['alice'] })

    const result = await getRecentSearches(1)

    expect(fetchApiMock).toHaveBeenCalledWith('/staff/search/recent?limit=1', {
      method: 'GET',
      token: 'token-123',
    })
    expect(result.success).toBe(true)
  })
})
