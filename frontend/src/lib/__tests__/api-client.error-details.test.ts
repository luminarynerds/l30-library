/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { fetchApi, ApiError, isApiError } from '../api-client'

afterEach(() => { vi.unstubAllGlobals() })

describe('api-client preserves error details', () => {
  it('puts the response body details array onto ApiError', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: 'Item is on hold for another patron',
          details: [{ hold_override: { hold_id: 5, held_patron_name: 'Jordan S.', patron_on_way: false, queue_length: 1 } }],
        }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      ),
    ))

    let caught: unknown
    try {
      await fetchApi('/staff/patrons/1/quick-checkout', { method: 'POST', token: 'tok', body: { barcode: 'X' } })
    } catch (e) {
      caught = e
    }

    expect(isApiError(caught)).toBe(true)
    const err = caught as ApiError
    expect(err.status).toBe(409)
    expect(Array.isArray(err.details)).toBe(true)
    // @ts-expect-error -- runtime shape check
    expect(err.details[0].hold_override.hold_id).toBe(5)
  })

  it('leaves details undefined when the response body has no details field', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ detail: 'Item not found' }),
        { status: 404, headers: { 'Content-Type': 'application/json' } },
      ),
    ))

    let caught: unknown
    try {
      await fetchApi('/catalog/items/999', { method: 'GET', token: 'tok' })
    } catch (e) {
      caught = e
    }

    expect(isApiError(caught)).toBe(true)
    expect((caught as ApiError).details).toBeUndefined()
  })
})
