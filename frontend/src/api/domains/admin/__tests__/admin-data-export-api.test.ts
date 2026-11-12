/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { getAccessToken } = vi.hoisted(() => ({
  getAccessToken: vi.fn(),
}))

vi.mock('@/utils/tokenStore', () => ({
  getAccessToken,
}))

vi.mock('@/lib/api-client', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

import { exportDataBundle } from '../admin-data-export-api'

describe('exportDataBundle', () => {
  beforeEach(() => {
    getAccessToken.mockReset()
    getAccessToken.mockReturnValue('test-token')
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('posts the passphrase with auth header and returns blob + sha256 + filename', async () => {
    const blob = new Blob(['zip-bytes'], { type: 'application/zip' })
    const headers = new Headers({
      'X-Export-SHA256': 'a'.repeat(64),
      'Content-Disposition': 'attachment; filename="l30-export-foo.zip"',
    })
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve(blob),
      headers,
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await exportDataBundle('correct horse battery')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const call = fetchMock.mock.calls[0]!
    const url = call[0] as string
    const init = call[1] as RequestInit & { headers: Record<string, string> }
    expect(url).toContain('/admin/data-export/bundle')
    expect(init.method).toBe('POST')
    expect(init.credentials).toBe('include')
    expect(init.headers.Authorization).toBe('Bearer test-token')
    expect(JSON.parse(init.body as string)).toEqual({ passphrase: 'correct horse battery' })

    expect(result.blob).toBe(blob)
    expect(result.sha256).toBe('a'.repeat(64))
    expect(result.filename).toBe('l30-export-foo.zip')
  })

  it('returns null sha256/filename when headers are absent', async () => {
    const blob = new Blob(['zip-bytes'], { type: 'application/zip' })
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: () => Promise.resolve(blob),
      headers: new Headers(),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await exportDataBundle('correct horse battery')
    expect(result.sha256).toBeNull()
    expect(result.filename).toBeNull()
  })

  it('throws on a non-ok response', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      blob: () => Promise.resolve(new Blob()),
      headers: new Headers(),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(exportDataBundle('correct horse battery')).rejects.toThrow('403')
  })
})
