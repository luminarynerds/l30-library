/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getAccessTokenMock } = vi.hoisted(() => ({
  getAccessTokenMock: vi.fn(),
}))

vi.mock('@/utils/tokenStore', () => ({
  getAccessToken: getAccessTokenMock,
  setAccessToken: vi.fn(),
}))

import { fetchApi, isApiError, setTokenRefresher } from '@/lib/api-client'

// The old client-side "no token -> block protected endpoint" preflight guard
// is gone BY DESIGN: auth now uses an httpOnly refresh cookie, so after a
// reload the access token is legitimately absent and the client must send the
// request, take the 401, refresh, and retry. These tests pin that flow.
describe('fetchApi auth behavior (401 refresh-retry)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getAccessTokenMock.mockReturnValue(null)
    setTokenRefresher(null)
    vi.stubGlobal('fetch', vi.fn())
  })

  it('sends protected requests without a token and surfaces the 401 when no refresher is set', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Not authenticated' }), { status: 401 })
    )

    await expect(fetchApi('/staff/dashboard/stats')).rejects.toMatchObject({ status: 401 })
    expect(global.fetch).toHaveBeenCalledOnce()
  })

  it('retries once with a fresh token after a 401 when a refresher is registered', async () => {
    setTokenRefresher(() => Promise.resolve('fresh-token'))
    vi.mocked(global.fetch)
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Not authenticated' }), { status: 401 })
      )
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }))

    await expect(fetchApi('/staff/dashboard/stats')).resolves.toEqual({ ok: true })

    expect(global.fetch).toHaveBeenCalledTimes(2)
    const retryCall = vi.mocked(global.fetch).mock.calls[1]!
    expect((retryCall[1]?.headers as Record<string, string>).Authorization).toBe(
      'Bearer fresh-token'
    )
  })

  it('does not attempt refresh-retry for auth endpoints (would loop)', async () => {
    setTokenRefresher(() => Promise.resolve('fresh-token'))
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Invalid credentials' }), { status: 401 })
    )

    await expect(fetchApi('/auth/login', { method: 'POST' })).rejects.toMatchObject({
      status: 401,
    })
    expect(global.fetch).toHaveBeenCalledOnce()
  })

  it('allows public endpoint requests when there is no token', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    )

    await expect(fetchApi('/auth/me')).resolves.toEqual({ ok: true })
    expect(global.fetch).toHaveBeenCalledOnce()
  })

  it('allows protected requests when token exists', async () => {
    getAccessTokenMock.mockReturnValue('token-123')
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    )

    await expect(fetchApi('/analytics/fines/summary')).resolves.toEqual({ ok: true })
    expect(global.fetch).toHaveBeenCalledOnce()
  })

  it('throws ApiError with isAuthError set for 401 responses', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Not authenticated' }), { status: 401 })
    )

    try {
      await fetchApi('/admin/users')
      throw new Error('Expected fetchApi to reject')
    } catch (error) {
      expect(isApiError(error)).toBe(true)
      if (isApiError(error)) {
        expect(error.isAuthError).toBe(true)
        expect(error.detail).toBe('Not authenticated')
      }
    }
  })
})
