/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { setTeacherCard, listSchoolPartnersForTeacherCard } from '../staff-management'
import * as apiClient from '@/lib/api-client'

vi.mock('@/lib/api-client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api-client')>('@/lib/api-client')
  return {
    ...actual,
    fetchApi: vi.fn(),
    isApiError: (e: unknown) => typeof e === 'object' && e !== null && 'status' in (e as Record<string, unknown>),
  }
})

const mockFetchApi = vi.mocked(apiClient.fetchApi)

describe('staff-management teacher card helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('setTeacherCard', () => {
    it('PATCHes the teacher-card endpoint with the school_id and returns the user', async () => {
      mockFetchApi.mockResolvedValue({ id: 42, role: 'teacher', school_id: 7 })

      const result = await setTeacherCard('tok', 42, 7)

      expect(mockFetchApi).toHaveBeenCalledTimes(1)
      const [path, opts] = mockFetchApi.mock.calls[0]!
      expect(path).toBe('/staff/patrons/42/teacher-card')
      expect(opts).toMatchObject({
        method: 'PATCH',
        token: 'tok',
        body: { school_id: 7 },
      })
      expect(result).toMatchObject({ role: 'teacher', school_id: 7 })
    })

    it('passes null school_id to revoke a teacher card', async () => {
      mockFetchApi.mockResolvedValue({ id: 42, role: 'patron', school_id: null })

      const result = await setTeacherCard('tok', 42, null)

      const [, opts] = mockFetchApi.mock.calls[0]!
      expect(opts).toMatchObject({
        method: 'PATCH',
        body: { school_id: null },
      })
      expect(result.role).toBe('patron')
    })

    it('throws a revoke-specific error when API fails with no detail and schoolId is null', async () => {
      mockFetchApi.mockRejectedValue({ status: 500, detail: '' })
      await expect(setTeacherCard('tok', 42, null)).rejects.toThrow(/revoke teacher card/i)
    })

    it('throws an issue-specific error when API fails with no detail and schoolId is provided', async () => {
      mockFetchApi.mockRejectedValue({ status: 500, detail: '' })
      await expect(setTeacherCard('tok', 42, 7)).rejects.toThrow(/issue teacher card/i)
    })

    it('preserves the backend detail message when present', async () => {
      mockFetchApi.mockRejectedValue({ status: 400, detail: 'School is closed' })
      await expect(setTeacherCard('tok', 42, 7)).rejects.toThrow('School is closed')
    })
  })

  describe('listSchoolPartnersForTeacherCard', () => {
    it('GETs /outreach/partners filtered to schools and returns the array', async () => {
      mockFetchApi.mockResolvedValue({
        partners: [
          { id: 1, name: 'Grant Elementary', partner_type: 'school' },
          { id: 2, name: 'Hillside High', partner_type: 'school' },
        ],
        total: 2,
        limit: 500,
        offset: 0,
      })

      const rows = await listSchoolPartnersForTeacherCard('tok')

      const [path, opts] = mockFetchApi.mock.calls[0]!
      expect(path).toContain('/outreach/partners')
      expect(path).toContain('partner_type=school')
      expect(path).toContain('limit=500')
      expect(opts).toMatchObject({ token: 'tok' })
      expect(rows).toHaveLength(2)
      expect(rows[0]!.name).toBe('Grant Elementary')
    })

    it('throws a friendly message on failure', async () => {
      mockFetchApi.mockRejectedValue({ status: 500, detail: '' })
      await expect(listSchoolPartnersForTeacherCard('tok')).rejects.toThrow(/load school partners/i)
    })
  })
})
