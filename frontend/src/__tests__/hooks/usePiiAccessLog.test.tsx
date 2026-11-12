/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { usePiiAccessLog } from '@/hooks/usePiiAccessLog'
import { logPiiAccess } from '@/api/domains/services/pii-access-log-api'

vi.mock('@/api/domains/services/pii-access-log-api', () => ({
  logPiiAccess: vi.fn(),
}))

const mocked = vi.mocked(logPiiAccess)

describe('usePiiAccessLog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocked.mockResolvedValue(null)
  })

  it('returns a stable callback across renders', () => {
    const { result, rerender } = renderHook(() => usePiiAccessLog())
    const first = result.current

    rerender()
    const second = result.current

    expect(first).toBe(second)
  })

  it('forwards the payload to logPiiAccess', () => {
    const { result } = renderHook(() => usePiiAccessLog())

    act(() => {
      result.current({
        patronId: 42,
        subjectType: 'patron_profile',
        action: 'reveal',
        reason: 'home visit prep',
      })
    })

    expect(mocked).toHaveBeenCalledTimes(1)
    expect(mocked).toHaveBeenCalledWith({
      patronId: 42,
      subjectType: 'patron_profile',
      action: 'reveal',
      reason: 'home visit prep',
    })
  })

  it('returns void (does not surface the api promise to the caller)', () => {
    const { result } = renderHook(() => usePiiAccessLog())

    const returned = result.current({
      patronId: 1,
      subjectType: 'home_address',
      action: 'read',
    })

    expect(returned).toBeUndefined()
  })

  it('swallows rejections from the underlying api', async () => {
    mocked.mockRejectedValueOnce(new Error('network'))
    const { result } = renderHook(() => usePiiAccessLog())

    expect(() => {
      result.current({
        patronId: 1,
        subjectType: 'minor_data',
        action: 'export',
      })
    }).not.toThrow()

    // Yield to the microtask queue so the rejected promise settles
    // without an unhandled-rejection warning.
    await act(async () => {
      await Promise.resolve()
    })
  })
})
