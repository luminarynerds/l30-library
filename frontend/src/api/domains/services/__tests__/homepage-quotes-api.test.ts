/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}))

vi.mock('@/lib/api-client', () => ({ api: apiMock }))

import {
  getHomepageQuotes,
  adminListHomepageQuotes,
  adminCreateHomepageQuote,
  adminUpdateHomepageQuote,
} from '../homepage-quotes-api'

const QUOTE = { id: 1, quote_text: 'Nah, who gave yall a whole building full of free books?', attribution: 'Druski' }
const ADMIN_QUOTE = { ...QUOTE, locale: 'en', is_active: true, display_order: 0 }

describe('homepage-quotes-api unwraps api-client responses', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
  })

  // api-client's api.{get,post,...} returns the parsed JSON body DIRECTLY -- not
  // an axios-style {data, status, headers} envelope. Treating the return as an
  // envelope (response.data) yields undefined and trips React Query with
  // "data is undefined", silently hiding the rotating quote section.
  it('returns the public quote array verbatim from api.get (no .data unwrap)', async () => {
    apiMock.get.mockResolvedValueOnce([QUOTE])
    const result = await getHomepageQuotes('en')
    expect(result).toEqual([QUOTE])
    expect(apiMock.get).toHaveBeenCalledWith('/homepage-quotes?locale=en')
  })

  it('returns the admin quote array verbatim from api.get', async () => {
    apiMock.get.mockResolvedValueOnce([ADMIN_QUOTE])
    const result = await adminListHomepageQuotes('en')
    expect(result).toEqual([ADMIN_QUOTE])
  })

  it('returns the created admin quote verbatim from api.post', async () => {
    apiMock.post.mockResolvedValueOnce(ADMIN_QUOTE)
    const result = await adminCreateHomepageQuote({ locale: 'en', quote_text: QUOTE.quote_text, attribution: 'Druski' })
    expect(result).toEqual(ADMIN_QUOTE)
  })

  it('returns the updated admin quote verbatim from api.put', async () => {
    apiMock.put.mockResolvedValueOnce(ADMIN_QUOTE)
    const result = await adminUpdateHomepageQuote(1, { attribution: 'Druski' })
    expect(result).toEqual(ADMIN_QUOTE)
  })
})
