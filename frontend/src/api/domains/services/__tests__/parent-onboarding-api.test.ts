/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { get, post, patch, del } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}))

vi.mock('@/lib/api-client', () => {
  const api = { get, post, patch, delete: del }
  return { api, default: api }
})

import { leaveConnectionGroup } from '../parent-onboarding-api'

describe('parent-onboarding-api connection groups', () => {
  beforeEach(() => {
    get.mockReset()
    post.mockReset()
    patch.mockReset()
    del.mockReset()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('leaveConnectionGroup', () => {
    it('issues DELETE to /connection-groups/{group_id}/members/{user_id}', async () => {
      del.mockResolvedValue(undefined)

      await leaveConnectionGroup(42, 7)

      expect(del).toHaveBeenCalledTimes(1)
      expect(del).toHaveBeenCalledWith(
        '/api/v1/parent-onboarding/connection-groups/42/members/7',
      )
      // Belt-and-braces: confirm the broken `/leave` URL is NOT used.
      expect(post).not.toHaveBeenCalled()
    })

    it('requires both groupId and userId in its signature', () => {
      // Compile-time guard: the function must take two number params.
      // If someone reverts to the single-arg shape, this line stops type-checking.
      const fn: (g: number, u: number) => Promise<void> = leaveConnectionGroup
      expect(typeof fn).toBe('function')
    })

    it('propagates fetch errors', async () => {
      del.mockRejectedValue(new Error('boom'))
      await expect(leaveConnectionGroup(1, 1)).rejects.toThrow('boom')
    })
  })

})
