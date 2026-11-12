/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

vi.mock('@/i18n', () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock('@/i18n/I18nContext', () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock('react-hot-toast', () => ({ default: { success: vi.fn(), error: vi.fn() } }))

import { useCheckout } from '../useCheckout'

afterEach(() => { vi.unstubAllGlobals() })

describe('useCheckout 409 hold_override chain', () => {
  it('sets holdOverride state when quick-checkout 409s with a hold_override block', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: 'Item is on hold for another patron',
          code: 'ITEM_ON_HOLD',
          details: [{ hold_override: { hold_id: 5, held_patron_name: 'Jordan S.', patron_on_way: false, queue_length: 1 } }],
        }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      ),
    ))

    const { result } = renderHook(() => useCheckout('test-token'))
    act(() => { result.current.setItemBarcode('BARCODE1') })
    await act(async () => {
      await result.current.handleCheckout(
        { preventDefault: () => {} } as unknown as React.FormEvent,
        42,
        () => {},
      )
    })

    expect(result.current.holdOverride).toEqual({
      holdId: 5,
      heldPatronName: 'Jordan S.',
      patronOnWay: false,
      queueLength: 1,
    })
  })
})
