/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchApi } from '@/lib/api-client'
import { getStaffActivityFeed, getStaffDashboardStats } from '../analytics'

vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: vi.fn(),
}))

describe('staff analytics api', () => {
  const mockFetchApi = vi.mocked(fetchApi)

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns dashboard stats from the API', async () => {
    const stats = {
      checkouts_today: 3,
      returns_today: 2,
      overdue_items: 1,
      active_holds: 4,
      new_patrons_this_week: 5,
      total_patrons: 6,
    }
    mockFetchApi.mockResolvedValueOnce(stats)

    await expect(getStaffDashboardStats('token')).resolves.toEqual(stats)
    expect(mockFetchApi).toHaveBeenCalledWith('/staff/dashboard/stats', { token: 'token' })
  })

  it('propagates the error when the dashboard stats API fails', async () => {
    mockFetchApi.mockRejectedValueOnce(new Error('boom'))

    await expect(getStaffDashboardStats('token')).rejects.toThrow('boom')
  })

  it('returns the activity feed array directly', async () => {
    const activity = [
      {
        id: 1,
        type: 'checkout' as const,
        description: 'Checked out a book',
        timestamp: '2026-01-01T00:00:00Z',
      },
    ]
    mockFetchApi.mockResolvedValueOnce(activity)

    await expect(getStaffActivityFeed('token', 25)).resolves.toEqual(activity)
    expect(mockFetchApi).toHaveBeenCalledWith('/staff/dashboard/activity?limit=25', { token: 'token' })
  })

  it('unwraps activity feed responses when data is nested', async () => {
    const activity = [
      {
        id: 2,
        type: 'return' as const,
        description: 'Returned a book',
        timestamp: '2026-01-02T00:00:00Z',
      },
    ]
    mockFetchApi.mockResolvedValueOnce({ data: activity })

    await expect(getStaffActivityFeed('token')).resolves.toEqual(activity)
  })


  it('maps backend activity envelope responses to UI activity shape', async () => {
    // patron_name is deliberately dropped: it's only shown on a specific
    // patron record, not on the general staff dashboard (see 7eec39abf).
    mockFetchApi.mockResolvedValueOnce({
      activities: [
        {
          activity_type: 'checkout',
          description: 'Checked out: Dune',
          patron_name: 'A. Patron',
          item_title: 'Dune',
          timestamp: '2026-01-03T00:00:00Z',
        },
      ],
    })

    await expect(getStaffActivityFeed('token')).resolves.toEqual([
      {
        id: 0,
        type: 'checkout',
        description: 'Checked out: Dune',
        item_title: 'Dune',
        timestamp: '2026-01-03T00:00:00Z',
      },
    ])
  })

  it('propagates the error when the activity feed API fails', async () => {
    mockFetchApi.mockRejectedValueOnce(new Error('activity failed'))

    await expect(getStaffActivityFeed('token')).rejects.toThrow('activity failed')
  })
})
