/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { get, post, put, del } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn(),
}))

vi.mock('@/lib/api-client', () => ({
  api: { get, post, put, delete: del },
}))

import {
  CIRCULATION_POLICY_ITEM_TYPES,
  CIRCULATION_POLICY_ROLES,
  BOOK_BINDINGS,
  createCirculationPolicy,
  deleteCirculationPolicy,
  describeScope,
  getCirculationPolicy,
  listCirculationPolicies,
  previewCirculationPolicy,
  updateCirculationPolicy,
  type CirculationPolicyResponse,
} from '../circulation-policy-api'

const samplePolicy: CirculationPolicyResponse = {
  id: 1,
  library_system_id: 1,
  role: 'child',
  item_type: 'book',
  binding: 'paperback',
  collection_id: null,
  loan_period_days: 21,
  max_renewals: 2,
  overdue_fine_per_day: '0.25',
  max_fine: '5.00',
  grace_period_days: 3,
  hold_pickup_days: 7,
  fine_free: false,
  active: true,
  notes: null,
  created_at: '2026-05-14T00:00:00Z',
  updated_at: null,
}

describe('circulation-policy-api', () => {
  beforeEach(() => {
    get.mockReset()
    post.mockReset()
    put.mockReset()
    del.mockReset()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('enums', () => {
    it('exports all 10 backend roles', () => {
      expect(CIRCULATION_POLICY_ROLES).toHaveLength(10)
      expect(CIRCULATION_POLICY_ROLES).toContain('homebond')
      expect(CIRCULATION_POLICY_ROLES).toContain('bookmobile')
    })
    it('exports all 7 book bindings', () => {
      expect(BOOK_BINDINGS).toHaveLength(7)
      expect(BOOK_BINDINGS).toContain('library_binding')
    })
    it('exports all 12 item types', () => {
      expect(CIRCULATION_POLICY_ITEM_TYPES).toHaveLength(12)
    })
  })

  describe('listCirculationPolicies', () => {
    it('GETs the list endpoint with passthrough params', async () => {
      get.mockResolvedValue([samplePolicy])
      const result = await listCirculationPolicies({ library_system_id: 1, role: 'child', active: true })
      expect(get).toHaveBeenCalledWith(
        '/staff/circulation-policies',
        { params: { library_system_id: 1, role: 'child', active: true } },
      )
      expect(result).toEqual([samplePolicy])
    })
    it('works with no params', async () => {
      get.mockResolvedValue([])
      await listCirculationPolicies()
      expect(get).toHaveBeenCalledWith('/staff/circulation-policies', { params: {} })
    })
  })

  describe('getCirculationPolicy', () => {
    it('GETs the policy by id', async () => {
      get.mockResolvedValue(samplePolicy)
      const result = await getCirculationPolicy(1)
      expect(get).toHaveBeenCalledWith('/staff/circulation-policies/1')
      expect(result).toEqual(samplePolicy)
    })
  })

  describe('createCirculationPolicy', () => {
    it('POSTs to the collection endpoint', async () => {
      post.mockResolvedValue(samplePolicy)
      await createCirculationPolicy({
        library_system_id: 1,
        role: 'child',
        loan_period_days: 21,
      })
      expect(post).toHaveBeenCalledWith(
        '/staff/circulation-policies',
        { library_system_id: 1, role: 'child', loan_period_days: 21 },
      )
    })
  })

  describe('updateCirculationPolicy', () => {
    it('PUTs to the policy endpoint', async () => {
      put.mockResolvedValue(samplePolicy)
      await updateCirculationPolicy(7, { active: false })
      expect(put).toHaveBeenCalledWith('/staff/circulation-policies/7', { active: false })
    })
  })

  describe('deleteCirculationPolicy', () => {
    it('DELETEs the policy endpoint', async () => {
      del.mockResolvedValue(undefined)
      await deleteCirculationPolicy(42)
      expect(del).toHaveBeenCalledWith('/staff/circulation-policies/42')
    })
  })

  describe('previewCirculationPolicy', () => {
    it('GETs preview with full param set', async () => {
      const resolved = {
        loan_period_days: 21,
        max_renewals: 2,
        overdue_fine_per_day: '0.25',
        max_fine: '5.00',
        grace_period_days: 3,
        hold_pickup_days: 7,
        fine_free: false,
        provenance: {
          loan_period_days: { policy_id: 1, scope: 'child' },
          max_renewals: { policy_id: null, scope: 'system default' },
          overdue_fine_per_day: { policy_id: 1, scope: 'child' },
          max_fine: { policy_id: null, scope: 'system default' },
          grace_period_days: { policy_id: null, scope: 'system default' },
          hold_pickup_days: { policy_id: null, scope: 'system default' },
          fine_free: { policy_id: 1, scope: 'child' },
        },
      }
      get.mockResolvedValue(resolved)
      const result = await previewCirculationPolicy({ role: 'child', item_type: 'book' })
      expect(get).toHaveBeenCalledWith(
        '/staff/circulation-policies/preview',
        { params: { role: 'child', item_type: 'book' } },
      )
      expect(result).toEqual(resolved)
    })
  })

  describe('describeScope', () => {
    it('renders NULL axes as em dash', () => {
      expect(describeScope({ role: null, item_type: null, binding: null, collection_id: null })).toEqual({
        role: '—',
        itemType: '—',
        binding: '—',
        collection: '—',
      })
    })
    it('renders set axes with human labels', () => {
      expect(describeScope({ role: 'child', item_type: 'book', binding: 'paperback', collection_id: 42 })).toEqual({
        role: 'Child',
        itemType: 'Book',
        binding: 'Paperback',
        collection: '#42',
      })
    })
  })
})
