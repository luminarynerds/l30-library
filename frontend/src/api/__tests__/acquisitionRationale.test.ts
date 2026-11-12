/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { get, post, put, MockApiError } = vi.hoisted(() => {
  class MockApiError extends Error {
    status: number
    detail: string
    isAuthError: boolean
    constructor(message: string, status: number) {
      super(message)
      this.name = 'ApiError'
      this.status = status
      this.detail = message
      this.isAuthError = status === 401 || status === 403
    }
  }
  return {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    MockApiError,
  }
})

vi.mock('@/lib/api-client', () => ({
  api: { get, post, put },
  isApiError: (e: unknown): e is InstanceType<typeof MockApiError> =>
    e instanceof MockApiError,
  ApiError: MockApiError,
}))

import {
  createRationale,
  getRationale,
  listBehaviorTags,
  listMissingRationale,
  listSignalCandidates,
  updateRationale,
} from '@/api/acquisitionRationale'
import type { AcquisitionRationale } from '@/types/acquisitionRationale'

const baseRationale: AcquisitionRationale = {
  id: 1,
  catalog_item_id: 5,
  created_by_id: 2,
  created_at: '2026-05-17T00:00:00Z',
  updated_at: '2026-05-17T00:00:00Z',
  signal_type: 'gap_in_collection',
  signal_ref_table: null,
  signal_ref_id: null,
  signal_note: null,
  policy_clause: null,
  primary_use_case_slug: 'new_parent',
  secondary_use_case_slugs: [],
  weeding_condition: 'current_5yr',
  weeding_signal_note: null,
  anticipated_challenge_reasons: [],
  anticipated_challenge_acknowledged: false,
  patron_visible: false,
  public_summary: null,
}

beforeEach(() => {
  get.mockReset()
  post.mockReset()
  put.mockReset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('acquisitionRationale API client', () => {
  it('getRationale returns parsed rationale on 200', async () => {
    get.mockResolvedValue(baseRationale)
    const result = await getRationale(5)
    expect(result).not.toBeNull()
    expect(result?.signal_type).toBe('gap_in_collection')
    expect(get).toHaveBeenCalledWith(
      expect.stringContaining('/catalog-items/5/acquisition-rationale'),
    )
  })

  it('getRationale returns null on 404', async () => {
    get.mockRejectedValue(new MockApiError('Not found', 404))
    const result = await getRationale(99)
    expect(result).toBeNull()
  })

  it('getRationale throws on non-404 error', async () => {
    get.mockRejectedValue(new MockApiError('Server error', 500))
    await expect(getRationale(5)).rejects.toThrow()
  })

  it('createRationale POSTs JSON body', async () => {
    post.mockResolvedValue(baseRationale)
    const payload = {
      signal_type: 'other' as const,
      primary_use_case_slug: 'new_parent',
      weeding_condition: 'current_5yr' as const,
    }
    await createRationale(5, payload)
    expect(post).toHaveBeenCalledWith(
      expect.stringContaining('/catalog-items/5/acquisition-rationale'),
      payload,
    )
  })

  it('updateRationale uses PUT', async () => {
    put.mockResolvedValue(baseRationale)
    await updateRationale(5, {
      signal_type: 'other' as const,
      primary_use_case_slug: 'new_parent',
      weeding_condition: 'current_5yr' as const,
    })
    expect(put).toHaveBeenCalledWith(
      expect.stringContaining('/catalog-items/5/acquisition-rationale'),
      expect.objectContaining({ signal_type: 'other' }),
    )
  })

  it('listBehaviorTags returns array', async () => {
    get.mockResolvedValue({
      tags: [
        {
          slug: 'new_parent',
          label: 'New parent',
          category: 'life_stage',
          description: null,
          sort_order: 10,
        },
      ],
    })
    const tags = await listBehaviorTags()
    expect(tags).toHaveLength(1)
    expect(tags[0]?.slug).toBe('new_parent')
  })

  it('listSignalCandidates returns array', async () => {
    get.mockResolvedValue({
      candidates: [
        {
          table_name: 'patron_purchase_requests',
          record_id: 1,
          summary: 'X',
          matched_on: 'isbn',
        },
      ],
    })
    const candidates = await listSignalCandidates(5)
    expect(candidates).toHaveLength(1)
    expect(candidates[0]?.table_name).toBe('patron_purchase_requests')
  })

  it('listMissingRationale returns ids', async () => {
    get.mockResolvedValue({ catalog_item_ids: [1, 2, 3], count: 3 })
    const ids = await listMissingRationale(50)
    expect(ids).toEqual([1, 2, 3])
    expect(get).toHaveBeenCalledWith(
      expect.stringContaining('/catalog-items/missing-rationale'),
      { params: { limit: 50 } },
    )
  })
})
