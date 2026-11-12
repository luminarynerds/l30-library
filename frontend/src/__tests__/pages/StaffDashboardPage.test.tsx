/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render } from '../utils/test-utils'
import { screen, waitFor } from "@testing-library/react"
import StaffDashboardPage from '../../pages/StaffDashboardPage'

// Hoist mocks so they're available at mock-factory time
const mocks = vi.hoisted(() => ({
  useDashboardProfile: vi.fn(),
  navigate: vi.fn(),
  toastError: vi.fn(),
}))

// Mock the dashboard profile hook so we control onboarding vs. shell branches.
vi.mock('@/hooks/useDashboardProfile', () => ({
  useDashboardProfile: mocks.useDashboardProfile,
}))

// Mock heavy child components — this test exercises the routing/auth-guard
// logic in StaffDashboardPage itself, not the inner dashboards. The real
// DashboardShell + DashboardOnboarding have their own deep dependency trees
// (react-query, lazy chunks, ToneContext, fair-scheduling API, etc.) that
// are out of scope for this file.
vi.mock('../../components/staff/dashboard/DashboardShell', () => ({
  default: () => <div data-testid="dashboard-shell">DashboardShell stub</div>,
}))

vi.mock('../../components/staff/dashboard/DashboardOnboarding', () => ({
  default: ({ userName }: { userName: string }) => (
    <div data-testid="dashboard-onboarding">Onboarding for {userName}</div>
  ),
}))

// AdminShell wraps content for sidebar-enabled functions; stub it out.
vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div data-testid="admin-shell" data-title={title}>{children}</div>
  ),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mocks.navigate }
})

vi.mock('react-hot-toast', () => ({
  default: { error: mocks.toastError, success: vi.fn(), info: vi.fn() },
}))

// Override the global AuthContext mock from setup.ts with an authenticated staff user.
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, first_name: 'Test', last_name: 'Staff', role: 'staff', email: 's@l30.org' },
    token: 'test-token',
    isLoading: false,
    isAuthenticated: true,
    sessionExpired: false,
    clearSessionExpired: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    updateProfile: vi.fn(),
    refreshUser: vi.fn(),
    showTimeoutWarning: false,
    timeoutSeconds: 120,
    dismissTimeoutWarning: vi.fn(),
    extendSession: vi.fn(),
    getSessionDuration: vi.fn(() => null),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

describe('StaffDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the onboarding flow when profile has no dashboard_functions', async () => {
    mocks.useDashboardProfile.mockReturnValue({
      profile: { dashboard_functions: null, dashboard_tone: 'standard' },
      isLoading: false,
      saveProfile: vi.fn(),
      needsOnboarding: true,
    })

    render(<StaffDashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-onboarding')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('dashboard-shell')).not.toBeInTheDocument()
  })

  it('renders DashboardShell when profile has at least one dashboard_function', async () => {
    mocks.useDashboardProfile.mockReturnValue({
      profile: { dashboard_functions: ['board_president'], dashboard_tone: 'standard' },
      isLoading: false,
      saveProfile: vi.fn(),
      needsOnboarding: false,
    })

    render(<StaffDashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-shell')).toBeInTheDocument()
    })
    expect(screen.getByText(/Staff Dashboard/i)).toBeInTheDocument()
    expect(screen.getByText(/Welcome back, Test/)).toBeInTheDocument()
    expect(screen.queryByTestId('dashboard-onboarding')).not.toBeInTheDocument()
  })

  it('wraps shell in AdminShell when default function is sidebar-enabled (front_desk)', async () => {
    mocks.useDashboardProfile.mockReturnValue({
      profile: { dashboard_functions: ['front_desk'], dashboard_tone: 'standard' },
      isLoading: false,
      saveProfile: vi.fn(),
      needsOnboarding: false,
    })

    render(<StaffDashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId('admin-shell')).toBeInTheDocument()
    })
    expect(screen.getByTestId('admin-shell')).toHaveAttribute('data-title', 'Staff Dashboard')
    expect(screen.getByTestId('dashboard-shell')).toBeInTheDocument()
  })
})
