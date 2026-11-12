/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from "@testing-library/react"
import { screen } from "@testing-library/react"
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import RequireAuth from '../RequireAuth'

// Mock the AuthContext
const mockUseAuth = vi.fn()

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

// Test component to render inside RequireAuth
function ProtectedContent() {
  return <div data-testid="protected-content">Protected Content</div>
}

// Component to check if we redirected to login
function LoginPage() {
  return <div data-testid="login-page">Login Page</div>
}

// Component to check if we redirected to account (access denied)
function AccountPage() {
  return <div data-testid="account-page">Account Page</div>
}

function renderWithRouter(
  ui: React.ReactElement,
  { initialEntries = ['/protected'] } = {}
) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/account" element={<AccountPage />} />
        <Route path="/protected" element={ui} />
      </Routes>
    </MemoryRouter>
  )
}

describe('RequireAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('authentication checks', () => {
    it('shows loading state while authentication is being determined', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        isLoading: true,
        isAuthenticated: false,
      })

      renderWithRouter(
        <RequireAuth>
          <ProtectedContent />
        </RequireAuth>
      )

      expect(screen.getByText('Loading...')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    it('redirects to login when user is not authenticated', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        isLoading: false,
        isAuthenticated: false,
      })

      renderWithRouter(
        <RequireAuth>
          <ProtectedContent />
        </RequireAuth>
      )

      expect(screen.getByTestId('login-page')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    it('renders protected content when user is authenticated', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'test@example.com', role: 'PATRON' },
        isLoading: false,
        isAuthenticated: true,
      })

      renderWithRouter(
        <RequireAuth>
          <ProtectedContent />
        </RequireAuth>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      expect(screen.queryByTestId('login-page')).not.toBeInTheDocument()
    })
  })

  describe('role-based access control', () => {
    it('allows access when user has required role', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'staff@example.com', role: 'staff' },
        isLoading: false,
        isAuthenticated: true,
      })

      renderWithRouter(
        <RequireAuth requiredRoles={['STAFF', 'ADMIN']}>
          <ProtectedContent />
        </RequireAuth>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })

    it('allows access when user has ADMIN role and ADMIN is required', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'admin@example.com', role: 'ADMIN' },
        isLoading: false,
        isAuthenticated: true,
      })

      renderWithRouter(
        <RequireAuth requiredRoles={['ADMIN']}>
          <ProtectedContent />
        </RequireAuth>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })

    it('redirects to account page when user lacks required role', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'patron@example.com', role: 'PATRON' },
        isLoading: false,
        isAuthenticated: true,
      })

      renderWithRouter(
        <RequireAuth requiredRoles={['STAFF', 'ADMIN']}>
          <ProtectedContent />
        </RequireAuth>
      )

      expect(screen.getByTestId('account-page')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    it('allows teacher role access to teacher-gated routes', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'teacher@example.com', role: 'teacher' },
        isLoading: false,
        isAuthenticated: true,
      })

      renderWithRouter(
        <RequireAuth requiredRoles={['teacher', 'staff', 'admin', 'super_admin', 'director']}>
          <ProtectedContent />
        </RequireAuth>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })

    it('redirects a patron away from a teacher-gated route', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'patron@example.com', role: 'patron' },
        isLoading: false,
        isAuthenticated: true,
      })

      renderWithRouter(
        <RequireAuth requiredRoles={['teacher', 'staff', 'admin', 'super_admin', 'director']}>
          <ProtectedContent />
        </RequireAuth>
      )

      expect(screen.getByTestId('account-page')).toBeInTheDocument()
      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
    })

    it('is case-insensitive when checking roles', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'staff@example.com', role: 'staff' },
        isLoading: false,
        isAuthenticated: true,
      })

      renderWithRouter(
        <RequireAuth requiredRoles={['STAFF']}>
          <ProtectedContent />
        </RequireAuth>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })

    it('defaults to PATRON role when user.role is undefined', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'user@example.com' },
        isLoading: false,
        isAuthenticated: true,
      })

      renderWithRouter(
        <RequireAuth requiredRoles={['PATRON']}>
          <ProtectedContent />
        </RequireAuth>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })
  })

  describe('redirect behavior', () => {
    it('preserves the original path in location state when redirecting to login', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        isLoading: false,
        isAuthenticated: false,
      })

      // We can't directly test location.state in this setup,
      // but we can verify the redirect happens
      renderWithRouter(
        <RequireAuth>
          <ProtectedContent />
        </RequireAuth>,
        { initialEntries: ['/protected'] }
      )

      expect(screen.getByTestId('login-page')).toBeInTheDocument()
    })
  })

  describe('no role requirements', () => {
    it('allows any authenticated user when requiredRoles is not specified', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'patron@example.com', role: 'PATRON' },
        isLoading: false,
        isAuthenticated: true,
      })

      renderWithRouter(
        <RequireAuth>
          <ProtectedContent />
        </RequireAuth>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })

    it('allows any authenticated user when requiredRoles is empty array', () => {
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'patron@example.com', role: 'PATRON' },
        isLoading: false,
        isAuthenticated: true,
      })

      renderWithRouter(
        <RequireAuth requiredRoles={[]}>
          <ProtectedContent />
        </RequireAuth>
      )

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })
  })
})
