/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { logPiiAccess } from '@/api/domains/services/pii-access-log-api'
import api from '@/lib/api-client'
import { addBreadcrumb } from '@/lib/sentry-lazy'

vi.mock('@/lib/api-client', () => ({
  default: { post: vi.fn() },
}))

vi.mock('@/lib/sentry-lazy', () => ({
  addBreadcrumb: vi.fn(),
}))

const mockedPost = vi.mocked(api.post)
const mockedBreadcrumb = vi.mocked(addBreadcrumb)

const RESPONSE = {
  id: 1,
  user_id: 7,
  patron_id: 42,
  subject_type: 'patron_profile',
  subject_id: 42,
  action: 'read',
  reason: null,
  accessed_at: '2026-05-18T00:00:00Z',
}

describe('logPiiAccess', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('POSTs the snake_case payload to /api/v1/pii-access-log/', async () => {
    mockedPost.mockResolvedValueOnce(RESPONSE)

    const result = await logPiiAccess({
      patronId: 42,
      subjectType: 'patron_profile',
      subjectId: 42,
      action: 'read',
      reason: 'reviewing application',
    })

    expect(mockedPost).toHaveBeenCalledTimes(1)
    expect(mockedPost).toHaveBeenCalledWith('/api/v1/pii-access-log/', {
      patron_id: 42,
      subject_type: 'patron_profile',
      subject_id: 42,
      action: 'read',
      reason: 'reviewing application',
    })
    expect(result).toEqual(RESPONSE)
  })

  it('omits subject_id and reason when not provided', async () => {
    mockedPost.mockResolvedValueOnce(RESPONSE)

    await logPiiAccess({
      patronId: 42,
      subjectType: 'home_address',
      action: 'reveal',
    })

    expect(mockedPost).toHaveBeenCalledWith('/api/v1/pii-access-log/', {
      patron_id: 42,
      subject_type: 'home_address',
      action: 'reveal',
    })
  })

  it('omits subject_id and reason when explicitly null', async () => {
    mockedPost.mockResolvedValueOnce(RESPONSE)

    await logPiiAccess({
      patronId: 42,
      subjectType: 'minor_data',
      action: 'export',
      subjectId: null,
      reason: null,
    })

    expect(mockedPost).toHaveBeenCalledWith('/api/v1/pii-access-log/', {
      patron_id: 42,
      subject_type: 'minor_data',
      action: 'export',
    })
  })

  it('returns null and logs a breadcrumb on api error', async () => {
    mockedPost.mockRejectedValueOnce(new Error('boom'))

    const result = await logPiiAccess({
      patronId: 42,
      subjectType: 'patron_profile',
      action: 'read',
    })

    expect(result).toBeNull()
    expect(mockedBreadcrumb).toHaveBeenCalledWith(
      expect.objectContaining({
        category: 'pii_access_log',
        level: 'warning',
        message: 'logPiiAccess failed',
        data: expect.objectContaining({
          patron_id: 42,
          subject_type: 'patron_profile',
          action: 'read',
          error: 'boom',
        }),
      }),
    )
  })

  it('never throws even when the api rejects with a non-Error value', async () => {
    mockedPost.mockRejectedValueOnce('string-error')

    const result = await logPiiAccess({
      patronId: 1,
      subjectType: 'patron_profile',
      action: 'print',
    })

    expect(result).toBeNull()
    expect(mockedBreadcrumb).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({ error: 'string-error' }),
      }),
    )
  })
})
