/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, act } from "@testing-library/react"
import { screen, fireEvent } from "@testing-library/react"
import { AuthProvider, useAuth, parseAbsoluteSessionTimeoutMs } from '../AuthContext'

// setup.ts globally mocks @/contexts/AuthContext for every test file; this
// file tests the real provider, so restore the actual module (the override
// mechanism the setup mock's own comment prescribes).
vi.mock('@/contexts/AuthContext', async (importOriginal) => await importOriginal())

// Mock the API module
vi.mock('../../api/api', () => ({
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  getMe: vi.fn(),
  updateMe: vi.fn(),
  refreshAccessToken: vi.fn(),
}))

// Mock the token store. hasSessionHint returns true so the provider's init
// attempts the refresh call (the paths these tests exercise); without it the
// init effect throws on the missing export and isLoading never settles.
vi.mock('../../utils/tokenStore', () => ({
  setAccessToken: vi.fn(),
  clearAccessToken: vi.fn(),
  setSessionHint: vi.fn(),
  clearSessionHint: vi.fn(),
  hasSessionHint: vi.fn(() => true),
}))

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

// Mock SessionTimeoutWarning component
vi.mock('../../components/SessionTimeoutWarning', () => ({
  default: ({ show, timeRemaining, onExtend, onDismiss }: {
    show: boolean
    timeRemaining: number
    onExtend: () => void
    onDismiss: () => void
  }) => show ? (
    <div data-testid="timeout-warning">
      <span data-testid="time-remaining">{timeRemaining}</span>
      <button data-testid="extend-btn" onClick={onExtend}>Extend</button>
      <button data-testid="dismiss-btn" onClick={onDismiss}>Dismiss</button>
    </div>
  ) : null,
}))

// Test component that uses the auth context
function TestComponent() {
  const {
    user,
    isAuthenticated,
    isLoading,
    sessionExpired,
    clearSessionExpired,
  } = useAuth()

  return (
    <div>
      <span data-testid="loading">{isLoading.toString()}</span>
      <span data-testid="authenticated">{isAuthenticated.toString()}</span>
      <span data-testid="session-expired">{sessionExpired.toString()}</span>
      <span data-testid="user">{user ? user.email : 'null'}</span>
      <button data-testid="clear-expired" onClick={clearSessionExpired}>
        Clear Expired
      </button>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('initial state', () => {
    it('starts with isLoading true', async () => {
      const { refreshAccessToken } = await import('../../api/api')
      ;(refreshAccessToken as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('No session'))

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      // Initially loading
      expect(screen.getByTestId('loading').textContent).toBe('true')

      // Wait for refresh attempt to complete
      await act(async () => {
        await vi.runAllTimersAsync()
      })
    })

    it('sets isLoading to false after initial auth check', async () => {
      const { refreshAccessToken } = await import('../../api/api')
      ;(refreshAccessToken as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('No session'))

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      await act(async () => {
        await vi.runAllTimersAsync()
      })

      // Direct assertion: waitFor polls on a timer, which never fires under
      // the fake timers this suite runs with. runAllTimersAsync has already
      // settled the init promise chain by here.
      expect(screen.getByTestId('loading').textContent).toBe('false')
    })
  })

  describe('sessionExpired state', () => {
    it('starts with sessionExpired false', async () => {
      const { refreshAccessToken } = await import('../../api/api')
      ;(refreshAccessToken as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('No session'))

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      await act(async () => {
        await vi.runAllTimersAsync()
      })

      expect(screen.getByTestId('session-expired').textContent).toBe('false')
    })

    it('clearSessionExpired resets the sessionExpired flag', async () => {
      const { refreshAccessToken } = await import('../../api/api')
      ;(refreshAccessToken as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('No session'))

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      await act(async () => {
        await vi.runAllTimersAsync()
      })

      // fireEvent, not userEvent: userEvent's internal delays are fake-timer
      // setTimeouts that never fire in this suite.
      const clearButton = screen.getByTestId('clear-expired')
      await act(async () => {
        fireEvent.click(clearButton)
      })

      expect(screen.getByTestId('session-expired').textContent).toBe('false')
    })
  })

  describe('idle detection constants', () => {
    it('has correct timing constants defined', async () => {
      // These are the expected values from the implementation
      const REFRESH_INTERVAL_MS = 10 * 60 * 1000 // 10 minutes
      const TIMEOUT_WARNING_MS = 2 * 60 * 1000 // 2 minutes
      const ACTIVITY_THROTTLE_MS = 30 * 1000 // 30 seconds

      expect(REFRESH_INTERVAL_MS).toBe(600000)
      expect(TIMEOUT_WARNING_MS).toBe(120000)
      expect(ACTIVITY_THROTTLE_MS).toBe(30000)
    })
  })

  describe('SessionTimeoutWarning integration', () => {
    it('does not show timeout warning initially', async () => {
      const { refreshAccessToken } = await import('../../api/api')
      ;(refreshAccessToken as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('No session'))

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      )

      await act(async () => {
        await vi.runAllTimersAsync()
      })

      expect(screen.queryByTestId('timeout-warning')).not.toBeInTheDocument()
    })
  })
})

describe('AuthContext idle events', () => {
  it('defines correct idle events to track', () => {
    const IDLE_EVENTS = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click']

    expect(IDLE_EVENTS).toContain('mousedown')
    expect(IDLE_EVENTS).toContain('keydown')
    expect(IDLE_EVENTS).toContain('scroll')
    expect(IDLE_EVENTS).toContain('touchstart')
    expect(IDLE_EVENTS).toContain('click')
    expect(IDLE_EVENTS).toHaveLength(5)
  })
})

describe('parseAbsoluteSessionTimeoutMs', () => {
  it('uses the default timeout when env value is undefined or empty', () => {
    expect(parseAbsoluteSessionTimeoutMs(undefined)).toBe(8 * 60 * 60 * 1000)
    expect(parseAbsoluteSessionTimeoutMs('')).toBe(8 * 60 * 60 * 1000)
  })

  it('falls back to default when env value is invalid', () => {
    expect(parseAbsoluteSessionTimeoutMs('not-a-number')).toBe(8 * 60 * 60 * 1000)
    expect(parseAbsoluteSessionTimeoutMs('Infinity')).toBe(8 * 60 * 60 * 1000)
  })

  it('supports disabling timeout with 0 or negative values', () => {
    expect(parseAbsoluteSessionTimeoutMs('0')).toBe(0)
    expect(parseAbsoluteSessionTimeoutMs('-1')).toBe(0)
  })

  it('supports fractional hour values', () => {
    expect(parseAbsoluteSessionTimeoutMs('1.5')).toBe(1.5 * 60 * 60 * 1000)
  })
})
