/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  getUpcomingClasses,
  getTechHelpOptions,
  getQuickAccessSections,
  getTechResources,
  getTechFacilities,
} from '@/api/tech-support-api'
import { fetchApi } from '@/lib/api-client'
import * as Sentry from '@/lib/sentry-lazy'

vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: (e: unknown) =>
    typeof e === 'object' && e !== null && 'detail' in e,
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

const mockedFetch = vi.mocked(fetchApi)
const mockedCapture = vi.mocked(Sentry.captureException)

describe('tech-support-api error propagation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Each fetcher must rethrow on failure instead of swallowing the error
  // and returning [] — an API outage should surface, not render as empty.
  const fetchers: ReadonlyArray<[string, () => Promise<unknown>]> = [
    ['getUpcomingClasses', getUpcomingClasses],
    ['getTechHelpOptions', getTechHelpOptions],
    ['getQuickAccessSections', getQuickAccessSections],
    ['getTechResources', () => getTechResources()],
    ['getTechFacilities', getTechFacilities],
  ]

  it.each(fetchers)('%s rejects (does not swallow) on ApiError', async (_name, fn) => {
    const apiError = { detail: 'service unavailable' }
    mockedFetch.mockRejectedValueOnce(apiError)

    await expect(fn()).rejects.toBe(apiError)
    expect(mockedCapture).toHaveBeenCalledTimes(1)
  })

  it.each(fetchers)('%s rejects (does not swallow) on non-ApiError', async (_name, fn) => {
    const genericError = new Error('network down')
    mockedFetch.mockRejectedValueOnce(genericError)

    await expect(fn()).rejects.toBe(genericError)
    expect(mockedCapture).toHaveBeenCalledTimes(1)
  })

  it('returns parsed data on success', async () => {
    const facilities = [{ kind: 'computer_lab', facilities: [] }]
    mockedFetch.mockResolvedValueOnce(facilities)

    await expect(getTechFacilities()).resolves.toEqual(facilities)
    expect(mockedCapture).not.toHaveBeenCalled()
  })

  it('getTechFacilities calls the facilities endpoint', async () => {
    mockedFetch.mockResolvedValueOnce([])

    await getTechFacilities()

    expect(mockedFetch).toHaveBeenCalledWith('/tech-support/facilities')
  })
})
