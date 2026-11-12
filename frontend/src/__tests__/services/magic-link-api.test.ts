/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Magic Link Auth API Tests
 *
 * Tests for magic link authentication API functions:
 * - requestMagicLink: sends a magic link email
 * - verifyMagicLink: verifies token and returns access token
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as apiClient from '@/lib/api-client'
import { AUTH_CONFIG } from '@/constants/authConfig'
import {
  requestMagicLink,
  verifyMagicLink,
} from '@/api/auth-api'

// Mock the api-client module
vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: vi.fn(),
}))

describe('Magic Link API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ==================== requestMagicLink Tests ====================

  describe('requestMagicLink', () => {
    it('should call the correct endpoint with email', async () => {
      const mockResponse = { message: 'If a verified account exists with that email, a sign-in link has been sent.' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await requestMagicLink('user@example.com')

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/magic-link', {
        method: 'POST',
        body: { email: 'user@example.com' },
      })
    })

    it('should send email in the request body', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ message: 'ok' })

      await requestMagicLink('patron@l30.org')

      const call = vi.mocked(apiClient.fetchApi).mock.calls[0]!
      const body = call[1]?.body as { email: string }
      expect(body.email).toBe('patron@l30.org')
    })

    it('should throw error when API returns error', async () => {
      const apiError = { status: 500, detail: 'Server error' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(requestMagicLink('user@example.com')).rejects.toThrow('Server error')
    })

    it('should throw default message when API error has no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(requestMagicLink('user@example.com')).rejects.toThrow('Failed to send magic link')
    })

    it('should re-throw non-API errors', async () => {
      const networkError = new Error('Network failure')
      vi.mocked(apiClient.fetchApi).mockRejectedValue(networkError)
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(requestMagicLink('user@example.com')).rejects.toThrow('Network failure')
    })
  })

  // ==================== verifyMagicLink Tests ====================

  describe('verifyMagicLink', () => {
    it('should call the correct endpoint with token', async () => {
      const mockResponse = { access_token: 'jwt-token-here', token_type: 'bearer' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await verifyMagicLink('magic-link-token-123')

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/magic-link/verify', {
        method: 'POST',
        body: { token: 'magic-link-token-123' },
      })
    })

    it('should return access token on success', async () => {
      const mockResponse = { access_token: 'new-access-token', token_type: 'bearer' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await verifyMagicLink('valid-token')

      expect(result.access_token).toBe('new-access-token')
      expect(result.token_type).toBe('bearer')
    })

    it('should prefer the backend detail for 423 (carries lockout duration)', async () => {
      const apiError = { status: 423, detail: 'Your account is locked for 30 minutes due to multiple failed login attempts.' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(verifyMagicLink('some-token')).rejects.toThrow(apiError.detail)
    })

    it('should throw warm locked-account copy for 423 without detail', async () => {
      const apiError = { status: 423 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(verifyMagicLink('some-token')).rejects.toThrow(
        AUTH_CONFIG.ERROR_MESSAGES.ACCOUNT_LOCKED
      )
    })

    it('should throw specific message for 401 status', async () => {
      const apiError = { status: 401, detail: 'Magic link has expired' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(verifyMagicLink('expired-token')).rejects.toThrow('Magic link has expired')
    })

    it('should throw default 401 message when no detail', async () => {
      const apiError = { status: 401 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(verifyMagicLink('bad-token')).rejects.toThrow('Invalid or expired magic link')
    })

    it('should throw generic message for other API errors', async () => {
      const apiError = { status: 500, detail: 'Internal server error' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(verifyMagicLink('some-token')).rejects.toThrow('Internal server error')
    })

    it('should throw default message for API errors without detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(verifyMagicLink('some-token')).rejects.toThrow('Magic link verification failed')
    })

    it('should re-throw non-API errors', async () => {
      const networkError = new Error('Connection timeout')
      vi.mocked(apiClient.fetchApi).mockRejectedValue(networkError)
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(verifyMagicLink('some-token')).rejects.toThrow('Connection timeout')
    })
  })
})
