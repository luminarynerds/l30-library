/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as apiClient from '@/lib/api-client'
import * as tokenStore from '@/utils/tokenStore'
import { getLearningPaths } from '@/api/learning-paths-api'

vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: vi.fn(),
}))

vi.mock('@/utils/tokenStore', () => ({
  getAccessToken: vi.fn(),
}))

describe('Learning Paths API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
  })

  it('serializes skip=0 in query params', async () => {
    vi.mocked(apiClient.fetchApi).mockResolvedValue([])

    await getLearningPaths({ skip: 0, limit: 10 })

    expect(apiClient.fetchApi).toHaveBeenCalledWith('/learning-paths?skip=0&limit=10', {
      token: 'test-token',
    })
  })
})
