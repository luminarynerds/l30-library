/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { withAuthFeature } from '../routeGuards'

// Mock both contexts that the wrappers depend on.
const mockUseAuth = vi.fn()
const mockUseOrgFeatures = vi.fn()

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('../../contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => mockUseOrgFeatures(),
}))

function Protected() {
  return <div data-testid="protected-content">Protected</div>
}

function LoginPage() {
  return <div data-testid="login-page">Login</div>
}

function NotFoundPage() {
  return <div data-testid="not-found">404</div>
}

function renderRoute(element: React.ReactElement) {
  return render(
    <MemoryRouter initialEntries={['/protected']}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/404" element={<NotFoundPage />} />
        <Route path="/protected" element={element} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('withAuthFeature', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('redirects anonymous users to /login even while feature flags are still loading', () => {
    // This is the critical race condition: feature flags fetch is in flight,
    // but the user is unambiguously not authenticated. We MUST redirect to
    // /login regardless of feature-flag load state, never spin on a "Loading..."
    // screen or render gated children optimistically.
    mockUseAuth.mockReturnValue({
      user: null,
      isLoading: false,
      isAuthenticated: false,
    })
    mockUseOrgFeatures.mockReturnValue({
      features: null,
      loading: true,
    })

    renderRoute(withAuthFeature('for_teachers_enabled', <Protected />))

    expect(screen.getByTestId('login-page')).toBeInTheDocument()
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
  })

  it('redirects anonymous users to /login when feature flags are resolved', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isLoading: false,
      isAuthenticated: false,
    })
    mockUseOrgFeatures.mockReturnValue({
      features: { for_teachers_enabled: true },
      loading: false,
    })

    renderRoute(withAuthFeature('for_teachers_enabled', <Protected />))

    expect(screen.getByTestId('login-page')).toBeInTheDocument()
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
  })

  it('renders the protected page for an authenticated user with the feature enabled', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'teacher@example.com', role: 'teacher' },
      isLoading: false,
      isAuthenticated: true,
    })
    mockUseOrgFeatures.mockReturnValue({
      features: { for_teachers_enabled: true },
      loading: false,
    })

    renderRoute(withAuthFeature('for_teachers_enabled', <Protected />))

    expect(screen.getByTestId('protected-content')).toBeInTheDocument()
  })

  it('shows the feature-disabled notice (not a 404) when authenticated but the feature is off', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'teacher@example.com', role: 'teacher' },
      isLoading: false,
      isAuthenticated: true,
    })
    mockUseOrgFeatures.mockReturnValue({
      features: { for_teachers_enabled: false },
      loading: false,
    })

    renderRoute(withAuthFeature('for_teachers_enabled', <Protected />))

    // A switched-off feature now reads as "turned off" with a way to re-enable
    // it, instead of a misleading "page not found".
    expect(
      screen.getByRole('heading', { name: /turned off/i }),
    ).toBeInTheDocument()
    expect(screen.queryByTestId('not-found')).not.toBeInTheDocument()
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
  })

  it('honors requiredRoles - allows access for matching role', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'teacher@example.com', role: 'teacher' },
      isLoading: false,
      isAuthenticated: true,
    })
    mockUseOrgFeatures.mockReturnValue({
      features: { for_teachers_enabled: true },
      loading: false,
    })

    renderRoute(
      withAuthFeature('for_teachers_enabled', <Protected />, [
        'teacher',
        'staff',
      ]),
    )

    expect(screen.getByTestId('protected-content')).toBeInTheDocument()
  })

  it('shows the auth-check spinner only while auth itself is resolving', () => {
    // While auth is genuinely loading we have to show *something*; the existing
    // RequireAuth spinner is acceptable. The bug is rendering it when auth has
    // already resolved to "not authenticated".
    mockUseAuth.mockReturnValue({
      user: null,
      isLoading: true,
      isAuthenticated: false,
    })
    mockUseOrgFeatures.mockReturnValue({
      features: null,
      loading: true,
    })

    renderRoute(withAuthFeature('for_teachers_enabled', <Protected />))

    expect(screen.getByText('Loading...')).toBeInTheDocument()
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    expect(screen.queryByTestId('login-page')).not.toBeInTheDocument()
  })
})
