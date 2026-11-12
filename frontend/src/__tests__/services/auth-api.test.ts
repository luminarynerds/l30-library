/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Auth API Service Tests
 *
 * Tests for authentication API functions including:
 * - Login/logout
 * - Registration
 * - Password management (forgot, reset, change)
 * - Email verification
 * - Session management
 * - Profile management
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as apiClient from '@/lib/api-client'
import { AUTH_CONFIG } from '@/constants/authConfig'
import {
  login,
  register,
  logout,
  refreshAccessToken,
  forgotPassword,
  resetPassword,
  verifyEmail,
  resendVerification,
  changePassword,
  getSessions,
  revokeSession,
  getMe,
  updateMe,
} from '@/api/auth-api'

// Mock the api-client module
vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: vi.fn(),
}))

describe('Auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ==================== Login Tests ====================

  describe('login', () => {
    it('should successfully login with valid credentials', async () => {
      const mockResponse = { access_token: 'test-token', token_type: 'bearer' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await login('test@example.com', 'password123')

      expect(result).toEqual(mockResponse)
      // login() Turnstile-gates itself (#882) — it pre-serializes the body
      // and sets Content-Type explicitly rather than letting fetchApi do it.
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'test@example.com', password: 'password123', turnstile_token: undefined }),
      })
    })

    it('should send credentials as JSON body', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ access_token: 'test', token_type: 'bearer' })

      await login('user@test.com', 'mypassword')

      const call = vi.mocked(apiClient.fetchApi).mock.calls[0]!
      const body = JSON.parse(call[1]?.body as string) as { email: string; password: string }
      expect(body.email).toBe('user@test.com')
      expect(body.password).toBe('mypassword')
    })

    // Error-message layering: auth-api maps failures to the warm patron-facing
    // copy in AUTH_CONFIG.ERROR_MESSAGES (b8e47395e). LoginPage displays the
    // AuthError message as-is. 423 prefers the backend detail because it
    // carries the configured lockout duration.

    it('should prefer the backend detail for 423 (carries lockout duration)', async () => {
      const apiError = { status: 423, detail: 'Your account is locked for 30 minutes due to multiple failed login attempts.' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(login('locked@test.com', 'password')).rejects.toThrow(apiError.detail)
    })

    it('should throw warm locked-account copy for 423 without detail', async () => {
      const apiError = { status: 423 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(login('locked@test.com', 'password')).rejects.toThrow(
        AUTH_CONFIG.ERROR_MESSAGES.ACCOUNT_LOCKED
      )
    })

    it('should throw warm rate-limit copy for 429', async () => {
      const apiError = { status: 429, detail: 'Rate limited' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(login('test@test.com', 'password')).rejects.toThrow(
        AUTH_CONFIG.ERROR_MESSAGES.RATE_LIMITED
      )
    })

    it('should throw warm invalid-credentials copy for 401, ignoring terse detail', async () => {
      const apiError = { status: 401, detail: 'Invalid credentials' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(login('test@test.com', 'wrongpassword')).rejects.toThrow(
        AUTH_CONFIG.ERROR_MESSAGES.INVALID_CREDENTIALS
      )
    })

    it('should throw warm invalid-credentials copy for 401 without detail', async () => {
      const apiError = { status: 401 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(login('test@test.com', 'password')).rejects.toThrow(
        AUTH_CONFIG.ERROR_MESSAGES.INVALID_CREDENTIALS
      )
    })

    it('should throw warm server-error copy for 500+, ignoring detail', async () => {
      const apiError = { status: 500, detail: 'Internal server error' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(login('test@test.com', 'password')).rejects.toThrow(
        AUTH_CONFIG.ERROR_MESSAGES.SERVER_ERROR
      )
    })

    it('should throw warm network copy for a fetch TypeError', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new TypeError('Failed to fetch'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(login('test@test.com', 'password')).rejects.toThrow(
        AUTH_CONFIG.ERROR_MESSAGES.NETWORK_ERROR
      )
    })

    it('should throw warm generic copy for unknown errors', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Something unexpected'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(login('test@test.com', 'password')).rejects.toThrow(
        AUTH_CONFIG.ERROR_MESSAGES.GENERIC_LOGIN_FAILED
      )
    })
  })

  // ==================== Register Tests ====================

  describe('register', () => {
    const validRegistrationData = {
      email: 'newuser@example.com',
      password: 'SecurePass123!',
      first_name: 'John',
      last_name: 'Doe',
    }

    it('should successfully register a new user', async () => {
      const mockUser = {
        id: 1,
        email: 'newuser@example.com',
        first_name: 'John',
        last_name: 'Doe',
        role: 'PATRON',
        is_active: true,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockUser)

      const result = await register(validRegistrationData)

      expect(result).toEqual(mockUser)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/register', {
        method: 'POST',
        body: validRegistrationData,
      })
    })

    it('should include optional fields when provided', async () => {
      const dataWithOptional = {
        ...validRegistrationData,
        phone: '555-1234',
        address: '123 Main St',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ id: 1 })

      await register(dataWithOptional)

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/register', {
        method: 'POST',
        body: dataWithOptional,
      })
    })

    it('should throw error for duplicate email', async () => {
      const apiError = { status: 409, detail: 'Email already registered' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(register(validRegistrationData)).rejects.toThrow('Email already registered')
    })

    it('should throw error for validation failures', async () => {
      const apiError = { status: 422, detail: 'Password too weak' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(register(validRegistrationData)).rejects.toThrow('Password too weak')
    })

    it('should throw warm generic register copy when no detail provided', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(register(validRegistrationData)).rejects.toThrow(
        AUTH_CONFIG.ERROR_MESSAGES.GENERIC_REGISTER_FAILED
      )
    })

    it('should throw warm network copy for a fetch TypeError', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new TypeError('Failed to fetch'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(register(validRegistrationData)).rejects.toThrow(
        AUTH_CONFIG.ERROR_MESSAGES.NETWORK_ERROR
      )
    })

    it('should throw warm generic register copy for unknown errors', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Connection refused'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(register(validRegistrationData)).rejects.toThrow(
        AUTH_CONFIG.ERROR_MESSAGES.GENERIC_REGISTER_FAILED
      )
    })
  })

  // ==================== Logout Tests ====================

  describe('logout', () => {
    it('should successfully logout', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue(undefined)

      await expect(logout('valid-token')).resolves.toBeUndefined()

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/logout', {
        method: 'POST',
        token: 'valid-token',
        skipJsonParse: true,
      })
    })

    it('should pass token in request', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue(undefined)

      await logout('my-auth-token')

      const call = vi.mocked(apiClient.fetchApi).mock.calls[0]!
      expect(call[1]?.token).toBe('my-auth-token')
    })
  })

  // ==================== Refresh Token Tests ====================

  describe('refreshAccessToken', () => {
    it('should successfully refresh token', async () => {
      const mockResponse = { access_token: 'new-token', token_type: 'bearer' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await refreshAccessToken()

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/refresh', {
        method: 'POST',
      })
    })

    it('should throw error when refresh fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Token expired'))

      await expect(refreshAccessToken()).rejects.toThrow('Failed to refresh token')
    })
  })

  // ==================== Forgot Password Tests ====================

  describe('forgotPassword', () => {
    it('should successfully send reset email', async () => {
      const mockResponse = { message: 'Reset email sent' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await forgotPassword('user@example.com')

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/forgot-password', {
        method: 'POST',
        body: { email: 'user@example.com' },
      })
    })

    it('should throw error for invalid email', async () => {
      const apiError = { status: 400, detail: 'Invalid email format' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(forgotPassword('invalid-email')).rejects.toThrow('Invalid email format')
    })

    it('should throw "Failed to send reset email" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(forgotPassword('user@example.com')).rejects.toThrow('Failed to send reset email')
    })

    it('should re-throw non-API errors', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Network timeout'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(forgotPassword('user@example.com')).rejects.toThrow('Network timeout')
    })
  })

  // ==================== Reset Password Tests ====================

  describe('resetPassword', () => {
    it('should successfully reset password', async () => {
      const mockResponse = { message: 'Password reset successful' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await resetPassword('reset-token', 'NewPassword123!')

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/reset-password', {
        method: 'POST',
        body: { token: 'reset-token', new_password: 'NewPassword123!' },
      })
    })

    it('should throw error for expired token', async () => {
      const apiError = { status: 400, detail: 'Token expired' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(resetPassword('expired-token', 'NewPass123')).rejects.toThrow('Token expired')
    })

    it('should throw error for weak password', async () => {
      const apiError = { status: 422, detail: 'Password does not meet requirements' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(resetPassword('valid-token', 'weak')).rejects.toThrow(
        'Password does not meet requirements'
      )
    })

    it('should throw "Failed to reset password" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(resetPassword('token', 'pass')).rejects.toThrow('Failed to reset password')
    })
  })

  // ==================== Verify Email Tests ====================

  describe('verifyEmail', () => {
    it('should successfully verify email', async () => {
      const mockResponse = { message: 'Email verified' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await verifyEmail('verification-token')

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/verify-email', {
        method: 'POST',
        body: { token: 'verification-token' },
      })
    })

    it('should throw error for invalid token', async () => {
      const apiError = { status: 400, detail: 'Invalid verification token' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(verifyEmail('invalid-token')).rejects.toThrow('Invalid verification token')
    })

    it('should throw "Failed to verify email" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(verifyEmail('token')).rejects.toThrow('Failed to verify email')
    })
  })

  // ==================== Resend Verification Tests ====================

  describe('resendVerification', () => {
    it('should successfully resend verification', async () => {
      const mockResponse = { message: 'Verification email sent' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await resendVerification('user@example.com')

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/resend-verification', {
        method: 'POST',
        body: { email: 'user@example.com' },
      })
    })

    it('should throw error for non-existent email', async () => {
      const apiError = { status: 404, detail: 'User not found' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(resendVerification('unknown@example.com')).rejects.toThrow('User not found')
    })

    it('should throw error for already verified email', async () => {
      const apiError = { status: 400, detail: 'Email already verified' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(resendVerification('verified@example.com')).rejects.toThrow(
        'Email already verified'
      )
    })

    it('should throw "Failed to resend verification" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(resendVerification('user@example.com')).rejects.toThrow(
        'Failed to resend verification'
      )
    })
  })

  // ==================== Change Password Tests ====================

  describe('changePassword', () => {
    it('should successfully change password', async () => {
      const mockResponse = { message: 'Password changed' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await changePassword('auth-token', 'OldPass123', 'NewPass456!')

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/change-password', {
        method: 'POST',
        token: 'auth-token',
        body: { current_password: 'OldPass123', new_password: 'NewPass456!' },
      })
    })

    it('should throw error for wrong current password', async () => {
      const apiError = { status: 400, detail: 'Current password is incorrect' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(changePassword('token', 'WrongPass', 'NewPass')).rejects.toThrow(
        'Current password is incorrect'
      )
    })

    it('should throw "Failed to change password" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(changePassword('token', 'old', 'new')).rejects.toThrow('Failed to change password')
    })
  })

  // ==================== Session Management Tests ====================

  describe('getSessions', () => {
    it('should return list of sessions', async () => {
      const mockSessions = {
        sessions: [
          { id: 1, device_info: 'Chrome', ip_address: '192.168.1.1', created_at: '2024-01-01', is_current: true },
          { id: 2, device_info: 'Firefox', ip_address: '192.168.1.2', created_at: '2024-01-02', is_current: false },
        ],
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockSessions)

      const result = await getSessions('auth-token')

      expect(result).toEqual(mockSessions)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/sessions', { token: 'auth-token' })
    })

    it('should throw error when fetch fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Unauthorized'))

      await expect(getSessions('invalid-token')).rejects.toThrow('Failed to get sessions')
    })
  })

  describe('revokeSession', () => {
    it('should successfully revoke session', async () => {
      const mockResponse = { message: 'Session revoked' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await revokeSession('auth-token', 123)

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/sessions/123', {
        method: 'DELETE',
        token: 'auth-token',
      })
    })

    it('should throw error when revoke fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Not found'))

      await expect(revokeSession('token', 999)).rejects.toThrow('Failed to revoke session')
    })
  })

  // ==================== Profile Management Tests ====================

  describe('getMe', () => {
    it('should return current user profile', async () => {
      const mockUser = {
        id: 1,
        email: 'user@example.com',
        first_name: 'John',
        last_name: 'Doe',
        role: 'PATRON',
        is_active: true,
        library_card: 'LIB123',
        phone: '555-1234',
        address: '123 Main St',
        email_verified: true,
        track_reading_history: true,
        created_at: '2024-01-01',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockUser)

      const result = await getMe('auth-token')

      expect(result).toEqual(mockUser)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/me', { token: 'auth-token' })
    })

    it('should throw error when not authenticated', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Unauthorized'))

      await expect(getMe('invalid-token')).rejects.toThrow('Failed to get user profile')
    })
  })

  describe('updateMe', () => {
    it('should successfully update profile', async () => {
      const updateData = { first_name: 'Jane', last_name: 'Smith' }
      const mockUpdatedUser = {
        id: 1,
        email: 'user@example.com',
        first_name: 'Jane',
        last_name: 'Smith',
        role: 'PATRON',
        is_active: true,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockUpdatedUser)

      const result = await updateMe('auth-token', updateData)

      expect(result).toEqual(mockUpdatedUser)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/me', {
        method: 'PUT',
        token: 'auth-token',
        body: updateData,
      })
    })

    it('should update phone number', async () => {
      const updateData = { phone: '555-9999' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ id: 1, phone: '555-9999' })

      await updateMe('auth-token', updateData)

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/me', {
        method: 'PUT',
        token: 'auth-token',
        body: { phone: '555-9999' },
      })
    })

    it('should update reading history preference', async () => {
      const updateData = { track_reading_history: false }
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ id: 1, track_reading_history: false })

      await updateMe('auth-token', updateData)

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/auth/me', {
        method: 'PUT',
        token: 'auth-token',
        body: { track_reading_history: false },
      })
    })

    it('should throw error for validation failure', async () => {
      const apiError = { status: 422, detail: 'Invalid phone format' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(updateMe('token', { phone: 'invalid' })).rejects.toThrow('Invalid phone format')
    })

    it('should throw "Update failed" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(updateMe('token', { first_name: 'Test' })).rejects.toThrow('Update failed')
    })

    it('should re-throw non-API errors', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Connection lost'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(updateMe('token', { first_name: 'Test' })).rejects.toThrow('Connection lost')
    })
  })
})
