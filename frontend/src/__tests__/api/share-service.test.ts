/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchSharingConfig, getShareStats, trackShare } from '@/api/share-service'
import { fetchApi } from '@/lib/api-client'

vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  getErrorMessage: (error: unknown) => (error instanceof Error ? error.message : String(error)),
}))

describe('share-service API integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchSharingConfig returns API data and caches it', async () => {
    const config = {
      sharing_enabled: true,
      share_buttons_enabled: true,
      share_counts_enabled: true,
      bluesky_enabled: true,
      mastodon_enabled: true,
      email_enabled: true,
      copy_link_enabled: true,
      utm_tracking_enabled: true,
      utm_source: 'newsletter',
      utm_medium: 'social',
    }
    vi.mocked(fetchApi).mockResolvedValue(config)

    const first = await fetchSharingConfig()
    const second = await fetchSharingConfig()

    expect(first).toEqual(config)
    expect(second).toEqual(config)
    expect(fetchApi).toHaveBeenCalledTimes(1)
  })

  it('trackShare returns the backend response payload', async () => {
    vi.mocked(fetchApi).mockResolvedValue({ success: true, message: 'tracked' })

    const result = await trackShare('book', 42, 'copy_link')

    expect(result).toEqual({ success: true, message: 'tracked' })
    expect(fetchApi).toHaveBeenCalledWith('/sharing/track?resource_type=book&resource_id=42&platform=copy_link', {
      method: 'POST',
    })
  })

  it('getShareStats returns stats from backend', async () => {
    const stats = {
      resource_type: 'book',
      resource_id: 5,
      total_shares: 1,
      bluesky_shares: 0,
      mastodon_shares: 0,
      reddit_shares: 0,
      email_shares: 0,
      copy_link_shares: 1,
      whatsapp_shares: 0,
      telegram_shares: 0,
      last_shared_at: null,
    }
    vi.mocked(fetchApi).mockResolvedValue(stats)

    const result = await getShareStats('book', 5)

    expect(result).toEqual(stats)
  })
})
