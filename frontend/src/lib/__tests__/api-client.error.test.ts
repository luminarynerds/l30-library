/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient, ApiError, isApiError } from '../api-client'
import { formatCardApplicationError } from '@/api/domains/patron/card-applications-api'

describe('api-client parseAndThrow', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  function mockFetchResponse(status: number, body: unknown): void {
    const json = JSON.stringify(body)
    global.fetch = vi.fn().mockResolvedValue(
      new Response(json, {
        status,
        headers: { 'Content-Type': 'application/json' },
      })
    )
  }

  it('captures raw body on ApiError for structured 409', async () => {
    mockFetchResponse(409, {
      detail: {
        message: 'Patron already has an active card.',
        existing_card_number: 'LSC-12345',
        user_id: 42,
      },
    })

    let caught: ApiError | null = null
    try {
      await apiClient('/card-applications/staff/1/review', { method: 'POST', body: {} })
    } catch (err) {
      if (isApiError(err)) caught = err
    }
    expect(caught).not.toBeNull()
    expect(caught!.status).toBe(409)
    expect(caught!.detail).toBe('Patron already has an active card.')
    expect(caught!.body).toEqual({
      detail: {
        message: 'Patron already has an active card.',
        existing_card_number: 'LSC-12345',
        user_id: 42,
      },
    })
  })

  it('keeps detail as a plain string for string-detail 4xx', async () => {
    mockFetchResponse(400, { detail: 'Email already registered.' })
    let caught: ApiError | null = null
    try {
      await apiClient('/card-applications', { method: 'POST', body: {} })
    } catch (err) {
      if (isApiError(err)) caught = err
    }
    expect(caught!.detail).toBe('Email already registered.')
    // Body is still the raw parsed JSON for callers that want it.
    expect(caught!.body).toEqual({ detail: 'Email already registered.' })
  })

  it('joins validation-array detail (422)', async () => {
    mockFetchResponse(422, {
      detail: [
        { msg: 'first_name: required' },
        { msg: 'email: invalid format' },
      ],
    })
    let caught: ApiError | null = null
    try {
      await apiClient('/card-applications', { method: 'POST', body: {} })
    } catch (err) {
      if (isApiError(err)) caught = err
    }
    expect(caught!.detail).toBe('first_name: required; email: invalid format')
  })
})

describe('formatCardApplicationError', () => {
  function makeApiError(status: number, detail: string, body?: unknown): ApiError {
    return new ApiError(detail, status, detail, undefined, body)
  }

  it('returns string detail unchanged', () => {
    const err = makeApiError(400, 'Email already registered.', { detail: 'Email already registered.' })
    expect(formatCardApplicationError(err, 'fallback')).toBe('Email already registered.')
  })

  it('renders structured 409 detail with hints', () => {
    const body = {
      detail: {
        message: 'Patron already has an active card.',
        existing_card_number: 'LSC-12345',
        user_id: 42,
      },
    }
    const err = makeApiError(409, 'Patron already has an active card.', body)
    const msg = formatCardApplicationError(err, 'fallback')
    expect(msg).toContain('Patron already has an active card.')
    expect(msg).toContain('LSC-12345')
  })

  it('falls back to the provided fallback for non-ApiError', () => {
    expect(formatCardApplicationError(new Error('boom'), 'fallback message')).toBe(
      'fallback message'
    )
  })

  it('falls back when ApiError has no detail and no structured body', () => {
    const err = makeApiError(500, '', undefined)
    expect(formatCardApplicationError(err, 'Failed to submit application')).toBe(
      'Failed to submit application'
    )
  })
})
