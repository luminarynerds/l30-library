/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchApi } from '@/lib/api-client'
import { staffCheckinItem } from '../circulation'

vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: vi.fn(),
}))

describe('staffCheckinItem', () => {
  const mockFetchApi = vi.mocked(fetchApi)

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns the backend {message, checkout} body unwrapped so checkoutId is defined', async () => {
    // Backend (app/api/v1/staff/circulation_checkin.py) returns:
    //   {"message": f"Checked in {item.title}", "checkout": checkout_response}
    // Regression: client used to type the body as Checkout and rewrap with a
    // hardcoded English message, dropping checkout.id and item_title.
    const checkout = {
      id: 42,
      user_id: 7,
      item_id: 9,
      status: 'returned' as const,
      checked_out_at: '2026-05-01T10:00:00Z',
      due_date: '2026-05-15T10:00:00Z',
      returned_at: '2026-05-18T10:00:00Z',
      item_title: 'Lord of the Rings',
      item_author: 'J.R.R. Tolkien',
    }
    mockFetchApi.mockResolvedValueOnce({
      message: 'Checked in Lord of the Rings',
      checkout,
    })

    const result = await staffCheckinItem('token', 'BC-42')

    expect(result.message).toBe('Checked in Lord of the Rings')
    expect(result.checkout.id).toBe(42)
    expect(result.checkout.item_title).toBe('Lord of the Rings')
    expect(mockFetchApi).toHaveBeenCalledWith('/staff/checkin-barcode?barcode=BC-42', {
      method: 'POST',
      token: 'token',
    })
  })
})
