/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * AuthContext Tests
 *
 * Tests for authentication context including:
 * - Token management (storage, refresh)
 * - Login flow (email and card)
 * - Logout flow
 * - Token refresh timer
 * - User state management
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, render } from "@testing-library/react"
import { waitFor } from "@testing-library/react"
import { Component, ReactNode } from 'react'
import * as api from '@/api/api'
import * as tokenStore from '@/utils/tokenStore'
import { mockUser, mockLoginResponse, mockRefreshResponse } from '../utils/mock-helpers'

// src/__tests__/setup.ts installs a global `vi.mock('@/contexts/AuthContext', ...)`
// with a static fake useAuth() (for pages/components that just need *some*
// auth context to render), so every test file gets the fake by default. This
// file is testing the real AuthContext, so it must opt back out.
vi.unmock('@/contexts/AuthContext')
const { AuthProvider, useAuth } = await import('@/contexts/AuthContext')

// Mock the API module
vi.mock('@/api/api', () => ({
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  getMe: vi.fn(),
  updateMe: vi.fn(),
  refreshAccessToken: vi.fn(),
}))

// Mock token store
vi.mock('@/utils/tokenStore', () => ({
  setAccessToken: vi.fn(),
  clearAccessToken: vi.fn(),
  getAccessToken: vi.fn(),
  // AuthContext gates the mount-time refresh attempt on a session hint (a
  // non-httpOnly cookie/flag) to avoid every anonymous page load firing a
  // doomed /auth/refresh call. Default to "hint present" so these tests keep
  // exercising the refresh-on-mount path they were written for.
  hasSessionHint: vi.fn(() => true),
  setSessionHint: vi.fn(),
  clearSessionHint: vi.fn(),
}))

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(tokenStore.hasSessionHint).mockReturnValue(true)
    // Set default mock for refreshAccessToken to reject (no valid session on mount)
    // Tests that need different behavior will override this
    vi.mocked(api.refreshAccessToken).mockRejectedValue(
      new Error('No refresh token'),
    )
  })

  afterEach(() => {
    // cleanup
  })

  const wrapper = ({ children }: { children: ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  )

  describe('Initial State', () => {
    it('should start with null user and token', () => {
      const { result } = renderHook(() => useAuth(), { wrapper })

      expect(result.current.user).toBeNull()
      expect(result.current.token).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
    })

    it('should set isLoading to true initially', () => {
      const { result } = renderHook(() => useAuth(), { wrapper })

      expect(result.current.isLoading).toBe(true)
    })

    it('should attempt to refresh token on mount', async () => {
      renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(api.refreshAccessToken).toHaveBeenCalledTimes(1)
      })
    })
  })

  describe('Login Flow', () => {
    it('should login with email credentials', async () => {
      vi.mocked(api.login).mockResolvedValue(mockLoginResponse)
      vi.mocked(api.getMe).mockResolvedValue(mockUser)

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        await result.current.login('test@example.com', 'password123')
      })

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser)
        expect(result.current.token).toBe(mockLoginResponse.access_token)
        expect(result.current.isAuthenticated).toBe(true)
      })

      // AuthContext forwards a (possibly undefined) Turnstile token as the 3rd arg.
      expect(api.login).toHaveBeenCalledWith('test@example.com', 'password123', undefined)
      expect(api.getMe).toHaveBeenCalledWith(mockLoginResponse.access_token)
      expect(tokenStore.setAccessToken).toHaveBeenCalledWith(mockLoginResponse.access_token)
    })

    it('should login with card number credentials', async () => {
      vi.mocked(api.login).mockResolvedValue(mockLoginResponse)
      vi.mocked(api.getMe).mockResolvedValue(mockUser)

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        await result.current.login('LSC123456', '1234')
      })

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true)
      })

      expect(api.login).toHaveBeenCalledWith('LSC123456', '1234', undefined)
    })

    it('should handle login errors', async () => {
      const error = new Error('Invalid credentials')
      vi.mocked(api.login).mockRejectedValue(error)

      const { result } = renderHook(() => useAuth(), { wrapper })

      await expect(
        act(async () => {
          await result.current.login('test@example.com', 'wrong')
        })
      ).rejects.toThrow('Invalid credentials')

      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
    })

    it('should start refresh timer after successful login', async () => {
      vi.useFakeTimers()
      // Override default to: first rejection (mount), then success (timer)
      vi.mocked(api.refreshAccessToken)
        .mockRejectedValueOnce(new Error('No refresh token'))
        .mockResolvedValueOnce(mockRefreshResponse)
      vi.mocked(api.login).mockResolvedValue(mockLoginResponse)
      vi.mocked(api.getMe).mockResolvedValue(mockUser)

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        await result.current.login('test@example.com', 'password123')
      })

      // Advance timer by 10 minutes (refresh interval)
      act(() => {
        vi.advanceTimersByTime(10 * 60 * 1000)
      })

      // With fake timers, the interval callback should have fired
      expect(api.refreshAccessToken).toHaveBeenCalledTimes(2) // mount + timer
      vi.useRealTimers()
    })
  })

  describe('Register Flow', () => {
    it('should register a new user and auto-login', async () => {
      const registerData = {
        email: 'new@example.com',
        password: 'password123',
        first_name: 'New',
        last_name: 'User',
      }

      vi.mocked(api.register).mockResolvedValue(mockUser)
      vi.mocked(api.login).mockResolvedValue(mockLoginResponse)
      vi.mocked(api.getMe).mockResolvedValue(mockUser)

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        await result.current.register(registerData)
      })

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true)
      })

      expect(api.register).toHaveBeenCalledWith(registerData)
      expect(api.login).toHaveBeenCalledWith(registerData.email, registerData.password, undefined)
    })
  })

  describe('Logout Flow', () => {
    it('should logout and clear user state', async () => {
      // Setup: login first
      vi.mocked(api.login).mockResolvedValue(mockLoginResponse)
      vi.mocked(api.getMe).mockResolvedValue(mockUser)
      vi.mocked(api.logout).mockResolvedValue(undefined)

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        await result.current.login('test@example.com', 'password123')
      })

      // Then logout
      await act(async () => {
        await result.current.logout()
      })

      await waitFor(() => {
        expect(result.current.user).toBeNull()
        expect(result.current.token).toBeNull()
        expect(result.current.isAuthenticated).toBe(false)
      })

      expect(api.logout).toHaveBeenCalledWith(mockLoginResponse.access_token)
      expect(tokenStore.clearAccessToken).toHaveBeenCalled()
    })

    it('should clear state even if logout API call fails', async () => {
      // Setup: login first
      vi.mocked(api.login).mockResolvedValue(mockLoginResponse)
      vi.mocked(api.getMe).mockResolvedValue(mockUser)
      vi.mocked(api.logout).mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        await result.current.login('test@example.com', 'password123')
      })

      // Logout should still clear local state
      await act(async () => {
        await result.current.logout()
      })

      await waitFor(() => {
        expect(result.current.user).toBeNull()
        expect(result.current.isAuthenticated).toBe(false)
      })
    })
  })

  describe('Token Refresh', () => {
    it('should refresh token successfully', async () => {
      vi.useFakeTimers()
      // Override default to: first rejection (mount), then success (timer)
      vi.mocked(api.refreshAccessToken)
        .mockRejectedValueOnce(new Error('No refresh token'))
        .mockResolvedValueOnce(mockRefreshResponse)
      vi.mocked(api.login).mockResolvedValue(mockLoginResponse)
      vi.mocked(api.getMe).mockResolvedValue(mockUser)

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        await result.current.login('test@example.com', 'password123')
      })

      const oldToken = result.current.token

      // Trigger refresh by advancing timer
      await act(async () => {
        vi.advanceTimersByTime(10 * 60 * 1000)
      })

      // With fake timers, state should be updated after advancing time
      expect(result.current.token).toBe(mockRefreshResponse.access_token)
      expect(result.current.token).not.toBe(oldToken)

      expect(tokenStore.setAccessToken).toHaveBeenCalledWith(mockRefreshResponse.access_token)
      vi.useRealTimers()
    })

    it('should clear auth state if token refresh fails', async () => {
      vi.useFakeTimers()
      // Both calls fail (mount and timer)
      vi.mocked(api.refreshAccessToken).mockRejectedValue(new Error('Refresh token expired'))
      vi.mocked(api.login).mockResolvedValue(mockLoginResponse)
      vi.mocked(api.getMe).mockResolvedValue(mockUser)

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        await result.current.login('test@example.com', 'password123')
      })

      // Trigger failed refresh
      await act(async () => {
        vi.advanceTimersByTime(10 * 60 * 1000)
      })

      // With fake timers, state should be updated after advancing time
      expect(result.current.user).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      vi.useRealTimers()
    })

    it('should restore session on page load with valid refresh token', async () => {
      // Override default to resolve (valid refresh token)
      vi.mocked(api.refreshAccessToken).mockResolvedValue(mockRefreshResponse)
      vi.mocked(api.getMe).mockResolvedValue(mockUser)

      const { result } = renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser)
        expect(result.current.token).toBe(mockRefreshResponse.access_token)
        expect(result.current.isLoading).toBe(false)
      })
    })
  })

  describe('Update Profile', () => {
    it('should update user profile', async () => {
      // Setup: login first
      vi.mocked(api.login).mockResolvedValue(mockLoginResponse)
      vi.mocked(api.getMe).mockResolvedValue(mockUser)

      const updatedUser = { ...mockUser, first_name: 'Updated' }
      vi.mocked(api.updateMe).mockResolvedValue(updatedUser)

      const { result } = renderHook(() => useAuth(), { wrapper })

      await act(async () => {
        await result.current.login('test@example.com', 'password123')
      })

      await act(async () => {
        await result.current.updateProfile({ first_name: 'Updated' })
      })

      await waitFor(() => {
        expect(result.current.user?.first_name).toBe('Updated')
      })

      expect(api.updateMe).toHaveBeenCalledWith(mockLoginResponse.access_token, {
        first_name: 'Updated',
      })
    })

    it('should throw error if not authenticated', async () => {
      vi.mocked(api.refreshAccessToken).mockRejectedValue(new Error('No token'))

      const { result } = renderHook(() => useAuth(), { wrapper })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      await expect(
        act(async () => {
          await result.current.updateProfile({ first_name: 'Updated' })
        })
      ).rejects.toThrow('Not authenticated')
    })
  })

  describe('Hook Error Handling', () => {
    it('should throw error if used outside AuthProvider', () => {
      // React 18's concurrent root (what RTL renders into by default) logs
      // render-phase errors via console.error / reportError instead of
      // re-throwing them synchronously to the renderHook() caller the way
      // the legacy ReactDOM.render root used to. An error boundary is the
      // supported way to observe a render throw under a concurrent root.
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

      let caught: Error | null = null
      class CaughtError extends Component<{ children: ReactNode }, { error: Error | null }> {
        state = { error: null as Error | null }
        static getDerivedStateFromError(error: Error) {
          return { error }
        }
        componentDidCatch(error: Error) {
          caught = error
        }
        render() {
          return this.state.error ? null : this.props.children
        }
      }

      const ThrowsOutsideProvider = () => {
        useAuth()
        return null
      }

      render(
        <CaughtError>
          <ThrowsOutsideProvider />
        </CaughtError>
      )

      expect(caught).not.toBeNull()
      expect((caught as unknown as Error).message).toBe('useAuth must be used within an AuthProvider')

      consoleError.mockRestore()
    })
  })
})
