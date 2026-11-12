/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * API Service Tests
 *
 * Tests for API helper functions including:
 * - GET, POST, PUT, DELETE requests
 * - Authentication token handling
 * - Error handling
 * - Response parsing
 *
 * `api` (default export of @/lib/api-client) always prefixes paths with
 * API_BASE ('/api/v1' in tests, since VITE_API_BASE is unset), sends
 * credentials: 'include' (so the httpOnly refresh cookie rides along), and
 * always sets Content-Type: application/json — even on GET/DELETE. Failed
 * requests reject with an ApiError instance (status + message + detail),
 * not a plain object.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import api from '@/lib/api-client'
import * as tokenStore from '@/utils/tokenStore'

// Mock token store
vi.mock('@/utils/tokenStore', () => ({
  getAccessToken: vi.fn(),
  setAccessToken: vi.fn(),
  clearAccessToken: vi.fn(),
}))

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('GET Requests', () => {
    it('should make GET request without token', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue(null)
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ data: 'test' }), { status: 200 }))

      await api.get('/api/test')

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/api/test', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      })
    })

    it('should make GET request with token', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ data: 'test' }), { status: 200 }))

      await api.get('/api/test')

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/api/test', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer test-token' },
      })
    })

    it('should return parsed JSON response', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue(null)
      const mockData = { id: 1, name: 'Test' }
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockData,
      })

      const result = await api.get('/api/test')

      expect(result).toEqual(mockData)
    })

    it('should throw error on failed request', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue(null)
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 }))

      await expect(api.get('/api/test')).rejects.toMatchObject({
        status: 404,
        message: 'Not found',
      })
    })

    it('should handle malformed error responses', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue(null)
      // A real Response whose body isn't valid JSON — exercises the
      // json()-throws fallback path in parseAndThrow without faking
      // Response internals. Fresh Response per call since the body can
      // only be read once.
      mockFetch.mockImplementation(async () => new Response('not valid json', { status: 500 }))

      await expect(api.get('/api/test')).rejects.toMatchObject({
        status: 500,
      })
      await expect(api.get('/api/test')).rejects.toBeInstanceOf(Error)
    })
  })

  describe('POST Requests', () => {
    it('should make POST request with data', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
      const postData = { name: 'Test', value: 123 }
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ id: 1, ...postData }), { status: 200 }))

      await api.post('/api/test', postData)

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/api/test', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-token',
        },
        body: JSON.stringify(postData),
      })
    })

    it('should make POST request without data', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ success: true }), { status: 200 }))

      await api.post('/api/test')

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/api/test', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-token',
        },
      })
    })

    it('should handle POST errors', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ detail: 'Invalid data' }), { status: 400 }))

      await expect(api.post('/api/test', { bad: 'data' })).rejects.toMatchObject({
        status: 400,
        message: 'Invalid data',
      })
    })
  })

  describe('PUT Requests', () => {
    it('should make PUT request with data', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
      const updateData = { name: 'Updated' }
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ id: 1, ...updateData }), { status: 200 }))

      await api.put('/api/test/1', updateData)

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/api/test/1', {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-token',
        },
        body: JSON.stringify(updateData),
      })
    })

    it('should handle PUT errors', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ detail: 'Forbidden' }), { status: 403 }))

      await expect(api.put('/api/test/1', { name: 'Updated' })).rejects.toMatchObject({
        status: 403,
        message: 'Forbidden',
      })
    })
  })

  describe('DELETE Requests', () => {
    it('should make DELETE request', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
      mockFetch.mockResolvedValue(new Response(null, { status: 204 }))

      const result = await api.delete('/api/test/1')

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/api/test/1', {
        method: 'DELETE',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer test-token' },
      })
      expect(result).toBeNull()
    })

    it('should return JSON for non-204 responses', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ message: 'Deleted' }),
      })

      const result = await api.delete('/api/test/1')

      expect(result).toEqual({ message: 'Deleted' })
    })

    it('should handle DELETE errors', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 }))

      await expect(api.delete('/api/test/1')).rejects.toMatchObject({
        status: 404,
        message: 'Not found',
      })
    })
  })

  describe('Authentication', () => {
    it('should include Bearer token in all authenticated requests', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token-123')
      // Fresh Response per call — a real Response body can only be read once,
      // and this test drives four requests off the same mock.
      mockFetch.mockImplementation(async () => new Response(JSON.stringify({}), { status: 200 }))

      await api.get('/api/test')
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token-123',
          }),
        })
      )

      await api.post('/api/test', {})
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token-123',
          }),
        })
      )

      await api.put('/api/test', {})
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token-123',
          }),
        })
      )

      await api.delete('/api/test')
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token-123',
          }),
        })
      )
    })

    it('should not include Authorization header when no token', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue(null)
      mockFetch.mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }))

      await api.get('/api/public')

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/api/public', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      })
    })
  })

  describe('Error Response Handling', () => {
    it('should handle 401 Unauthorized', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('expired-token')
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ detail: 'Unauthorized' }), { status: 401 }))

      await expect(api.get('/api/protected')).rejects.toMatchObject({
        status: 401,
        message: 'Unauthorized',
      })
    })

    it('should handle 403 Forbidden', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ detail: 'Forbidden' }), { status: 403 }))

      await expect(api.get('/api/admin')).rejects.toMatchObject({
        status: 403,
        message: 'Forbidden',
      })
    })

    it('should handle 500 Server Error', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue(null)
      mockFetch.mockResolvedValue(new Response(JSON.stringify({ detail: 'Internal server error' }), { status: 500 }))

      await expect(api.get('/api/test')).rejects.toMatchObject({
        status: 500,
        message: 'Internal server error',
      })
    })

    it('should handle network errors', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue(null)
      mockFetch.mockRejectedValue(new Error('Network error'))

      await expect(api.get('/api/test')).rejects.toThrow('Network error')
    })
  })

  describe('Response Parsing', () => {
    it('should parse JSON responses correctly', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue(null)

      const testCases = [
        { input: { id: 1 }, expected: { id: 1 } },
        { input: [], expected: [] },
        { input: { nested: { data: [1, 2, 3] } }, expected: { nested: { data: [1, 2, 3] } } },
        { input: null, expected: null },
      ]

      for (const { input, expected } of testCases) {
        mockFetch.mockResolvedValue({
          ok: true,
          json: async () => input,
        })

        const result = await api.get('/api/test')
        expect(result).toEqual(expected)
      }
    })
  })

  describe('Content-Type Headers', () => {
    it('should set Content-Type for POST requests', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue(null)
      mockFetch.mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }))

      await api.post('/api/test', { data: 'test' })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      )
    })

    it('should set Content-Type for PUT requests', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue(null)
      mockFetch.mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }))

      await api.put('/api/test', { data: 'test' })

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      )
    })
  })
})
