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
}))

import { notificationAPI } from '@/api/notifications-api'

describe('notificationAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('blocks unauthenticated notification requests', async () => {
    getAccessTokenMock.mockReturnValue(null)

    await expect(notificationAPI.getNotifications()).rejects.toThrow('Authentication required')
    expect(fetchApiMock).not.toHaveBeenCalled()
  })

  it('uses token when marking as read', async () => {
    getAccessTokenMock.mockReturnValue('token-123')
    fetchApiMock.mockResolvedValueOnce({ ok: true })

    await notificationAPI.markAsRead('n1')

    expect(fetchApiMock).toHaveBeenCalledWith('/notifications/live/n1/read', {
      method: 'POST',
      token: 'token-123',
    })
  })
})
