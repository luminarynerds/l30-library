/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * RegisterPage Tests
 *
 * Tests for registration page including:
 * - Form validation
 * - Registration submission
 * - Error handling
 * - Password strength validation
 * - Terms acceptance
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '../utils/test-utils'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RegisterPage from '@/pages/RegisterPage'
import { mockUser } from '../utils/mock-helpers'

// Mock the auth context (hoisted for vi.mock factory compatibility)
const { mockRegister, mockUseAuth } = vi.hoisted(() => {
  const mockRegister = vi.fn()
  return {
    mockRegister,
    mockUseAuth: {
      register: mockRegister,
      login: vi.fn(),
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
      sessionExpired: false,
      clearSessionExpired: vi.fn(),
      logout: vi.fn(),
      updateProfile: vi.fn(),
      refreshUser: vi.fn(),
      showTimeoutWarning: false,
      timeoutSeconds: 120,
      dismissTimeoutWarning: vi.fn(),
      extendSession: vi.fn(),
      getSessionDuration: vi.fn(() => null),
    },
  }
})

vi.mock('@/contexts/AuthContext', async () => {
  const React = await import('react')
  return {
    useAuth: () => mockUseAuth,
    AuthProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
    default: mockUseAuth,
  }
})
vi.mock('../../contexts/AuthContext', async () => {
  const React = await import('react')
  return {
    useAuth: () => mockUseAuth,
    AuthProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
    default: mockUseAuth,
  }
})

// RegisterPage was rewritten (#1484) as an invite-only waiting-list form: it
// posts to /waitlist via fetchApi directly and no longer uses AuthContext at
// all. Mock fetchApi so we can drive loading/success/error states.
const { mockFetchApi } = vi.hoisted(() => ({ mockFetchApi: vi.fn() }))
vi.mock('@/api/fetchApi', () => ({
  fetchApi: (...args: unknown[]) => mockFetchApi(...args),
}))

describe('RegisterPage', () => {
  // Preload English translations. vitest setup.ts does not preload i18n,
  // and assertions like getByText(/Join Our Library/i) / getByLabelText(/First Name/i)
  // only succeed when the English copy is in the module-level cache.

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchApi.mockResolvedValue({})
  })

  const renderRegisterPage = () => {
    return render(
      <MemoryRouter initialEntries={['/register']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/account" element={<div>Account Page</div>} />
        </Routes>
      </MemoryRouter>
    )
  }

  describe('Initial Render', () => {
    it('should render registration page with title', () => {
      renderRegisterPage()

      // RegisterPage was rewritten (#1484) as an invite-only waiting-list
      // form ("Join the waiting list"); it no longer creates an account
      // directly ("Join Our Library" no longer exists on this page).
      expect(screen.getByRole('heading', { name: /Join the waiting list/i })).toBeInTheDocument()
    })

    it('should render all form fields', () => {
      renderRegisterPage()

      // Self-serve account creation (name/password fields) moved out of
      // this page; the waiting-list form only collects an email address.
      expect(screen.getByLabelText(/Email/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Join the waiting list/i })).toBeInTheDocument()
    })

    it('should have a continue button on step 1', () => {
      renderRegisterPage()

      // No more multi-step flow: the single-step form submits directly
      // with a "Join the waiting list" button (no "Continue" step).
      expect(screen.getByRole('button', { name: /Join the waiting list/i })).toBeInTheDocument()
    })

    // SKIPPED: terms checkbox is on step 2 of multi-step flow, not step 1.
    it.skip('should have terms and conditions checkbox', () => {
      renderRegisterPage()

      expect(
        screen.getByRole('checkbox', { name: /I agree to the Terms/i })
      ).toBeInTheDocument()
    })
  })

  // SKIPPED: RegisterPage is now a 2-step flow, confirm-password field removed,
  // and HTML5 validation intercepts most validators before JS runs.
  describe.skip('Form Validation', () => {
    it('should validate required fields', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.click(screen.getByRole('button', { name: /Create Account/i }))

      await waitFor(() => {
        expect(screen.getByText(/First name is required/i)).toBeInTheDocument()
        expect(screen.getByText(/Last name is required/i)).toBeInTheDocument()
        expect(screen.getByText(/Email is required/i)).toBeInTheDocument()
      })

      expect(mockRegister).not.toHaveBeenCalled()
    })

    it('should validate email format', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/Email Address/i), 'invalid-email')
      await user.click(screen.getByRole('button', { name: /Create Account/i }))

      await waitFor(() => {
        expect(screen.getByText(/Enter a valid email address/i)).toBeInTheDocument()
      })
    })

    it('should validate password length', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/Create a Password/i), 'short')
      await user.click(screen.getByRole('button', { name: /Create Account/i }))

      await waitFor(() => {
        expect(
          screen.getByText(/Password must be at least 8 characters/i)
        ).toBeInTheDocument()
      })
    })

    it('should validate password confirmation matches', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/Create a Password/i), 'Secur3Pass!')
      await user.type(screen.getByLabelText(/Confirm.*Password/i), 'different123')
      await user.click(screen.getByRole('button', { name: /Create Account/i }))

      await waitFor(() => {
        expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument()
      })
    })

    it('should require terms acceptance', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.type(screen.getByLabelText(/First Name/i), 'Test')
      await user.type(screen.getByLabelText(/Last Name/i), 'User')
      await user.type(screen.getByLabelText(/Email Address/i), 'test@example.com')
      await user.type(screen.getByLabelText(/Create a Password/i), 'Secur3Pass!')
      await user.type(screen.getByLabelText(/Confirm.*Password/i), 'Secur3Pass!')

      await user.click(screen.getByRole('button', { name: /Create Account/i }))

      await waitFor(() => {
        expect(
          screen.getByText(/You must accept the terms and conditions/i)
        ).toBeInTheDocument()
      })
    })
  })

  // RENAMED from "Password Strength": password creation moved off this page
  // entirely (#1484) — RegisterPage has no password field to measure
  // strength on. Coverage retargeted to the waiting-list submission
  // feedback states that replaced it (loading, then success).
  describe('Submission Feedback', () => {
    it('should show a loading indicator while submitting', async () => {
      const user = userEvent.setup()
      let resolveSubmit: (value: unknown) => void = () => {}
      mockFetchApi.mockImplementation(
        () => new Promise(resolve => { resolveSubmit = resolve })
      )

      renderRegisterPage()

      await user.type(screen.getByLabelText(/Email/i), 'test@example.com')
      await user.click(screen.getByRole('button', { name: /Join the waiting list/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Joining/i })).toBeDisabled()
      })

      resolveSubmit({})
    })

    it('should show a confirmation message after successful submission', async () => {
      const user = userEvent.setup()
      mockFetchApi.mockResolvedValue({})

      renderRegisterPage()

      await user.type(screen.getByLabelText(/Email/i), 'test@example.com')
      await user.click(screen.getByRole('button', { name: /Join the waiting list/i }))

      await waitFor(() => {
        expect(screen.getByRole('status')).toHaveTextContent(/you're on the list/i)
      })
    })
  })

  // SKIPPED: multi-step flow + removed confirm-password — tests need rewrite.
  describe.skip('Successful Registration', () => {
    it('should register with valid data', async () => {
      const user = userEvent.setup()
      mockRegister.mockResolvedValue(mockUser)

      renderRegisterPage()

      await user.type(screen.getByLabelText(/First Name/i), 'Test')
      await user.type(screen.getByLabelText(/Last Name/i), 'User')
      await user.type(screen.getByLabelText(/Email Address/i), 'test@example.com')
      await user.type(screen.getByLabelText(/Create a Password/i), 'Secur3Pass!')
      await user.type(screen.getByLabelText(/Confirm.*Password/i), 'Secur3Pass!')
      await user.click(screen.getByRole('checkbox', { name: /I agree to the Terms/i }))

      await user.click(screen.getByRole('button', { name: /Create Account/i }))

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalledWith({
          first_name: 'Test',
          last_name: 'User',
          email: 'test@example.com',
          password: 'Secur3Pass!',
        })
      })
    })

    it('should navigate to account page after successful registration', async () => {
      const user = userEvent.setup()
      mockRegister.mockResolvedValue(mockUser)

      renderRegisterPage()

      await user.type(screen.getByLabelText(/First Name/i), 'Test')
      await user.type(screen.getByLabelText(/Last Name/i), 'User')
      await user.type(screen.getByLabelText(/Email Address/i), 'test@example.com')
      await user.type(screen.getByLabelText(/Create a Password/i), 'Secur3Pass!')
      await user.type(screen.getByLabelText(/Confirm.*Password/i), 'Secur3Pass!')
      await user.click(screen.getByRole('checkbox', { name: /I agree to the Terms/i }))

      await user.click(screen.getByRole('button', { name: /Create Account/i }))

      await waitFor(() => {
        expect(screen.getByText('Account Page')).toBeInTheDocument()
      })
    })
  })

  // SKIPPED: multi-step flow + removed confirm-password — tests need rewrite.
  describe.skip('Error Handling', () => {
    it('should display error when registration fails', async () => {
      const user = userEvent.setup()
      mockRegister.mockRejectedValue(new Error('Email already exists'))

      renderRegisterPage()

      await user.type(screen.getByLabelText(/First Name/i), 'Test')
      await user.type(screen.getByLabelText(/Last Name/i), 'User')
      await user.type(screen.getByLabelText(/Email Address/i), 'existing@example.com')
      await user.type(screen.getByLabelText(/Create a Password/i), 'Secur3Pass!')
      await user.type(screen.getByLabelText(/Confirm.*Password/i), 'Secur3Pass!')
      await user.click(screen.getByRole('checkbox', { name: /I agree to the Terms/i }))

      await user.click(screen.getByRole('button', { name: /Create Account/i }))

      await waitFor(() => {
        expect(screen.getByText(/Email already exists/i)).toBeInTheDocument()
      })
    })

    it('should display generic error for unexpected failures', async () => {
      const user = userEvent.setup()
      mockRegister.mockRejectedValue(new Error('Network error'))

      renderRegisterPage()

      await user.type(screen.getByLabelText(/First Name/i), 'Test')
      await user.type(screen.getByLabelText(/Last Name/i), 'User')
      await user.type(screen.getByLabelText(/Email Address/i), 'test@example.com')
      await user.type(screen.getByLabelText(/Create a Password/i), 'Secur3Pass!')
      await user.type(screen.getByLabelText(/Confirm.*Password/i), 'Secur3Pass!')
      await user.click(screen.getByRole('checkbox', { name: /I agree to the Terms/i }))

      await user.click(screen.getByRole('button', { name: /Create Account/i }))

      await waitFor(() => {
        expect(screen.getByText(/Network error/i)).toBeInTheDocument()
      })
    })
  })

  // SKIPPED: multi-step flow changes mean loading state is different now.
  describe.skip('Loading State', () => {
    it('should disable form during registration', async () => {
      const user = userEvent.setup()
      mockRegister.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      renderRegisterPage()

      await user.type(screen.getByLabelText(/First Name/i), 'Test')
      await user.type(screen.getByLabelText(/Last Name/i), 'User')
      await user.type(screen.getByLabelText(/Email Address/i), 'test@example.com')
      await user.type(screen.getByLabelText(/Create a Password/i), 'Secur3Pass!')
      await user.type(screen.getByLabelText(/Confirm.*Password/i), 'Secur3Pass!')
      await user.click(screen.getByRole('checkbox', { name: /I agree to the Terms/i }))

      const submitButton = screen.getByRole('button', { name: /Create Account/i })
      await user.click(submitButton)

      expect(submitButton).toBeDisabled()
    })
  })

  // RENAMED from "Password Visibility Toggle": no password field remains on
  // this page to have a visibility toggle. Coverage retargeted to the
  // waiting-list submission's own error-handling behavior.
  describe('Error Handling', () => {
    it('should show an error message when the waitlist submission fails', async () => {
      const user = userEvent.setup()
      mockFetchApi.mockRejectedValue({ message: 'Email already on the waiting list' })

      renderRegisterPage()

      await user.type(screen.getByLabelText(/Email/i), 'test@example.com')
      await user.click(screen.getByRole('button', { name: /Join the waiting list/i }))

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(/Email already on the waiting list/i)
      })
    })
  })

  describe('Navigation Links', () => {
    it('should have link to login page', () => {
      renderRegisterPage()

      const loginLink = screen.getByRole('link', { name: /Sign in/i })
      expect(loginLink).toBeInTheDocument()
      expect(loginLink).toHaveAttribute('href', '/login')
    })
  })

  describe('Accessibility', () => {
    it('should have proper form labels', () => {
      renderRegisterPage()

      // Only field remaining on the waiting-list form is Email.
      expect(screen.getByLabelText(/Email/i)).toBeInTheDocument()
    })

    // SKIPPED: HTML5 validation pre-empts JS validation so no accessible
    // description is attached on empty-submit in the current flow.
    it.skip('should associate error messages with inputs', async () => {
      const user = userEvent.setup()
      renderRegisterPage()

      await user.click(screen.getByRole('button', { name: /Create Account/i }))

      await waitFor(() => {
        const firstNameInput = screen.getByLabelText(/First Name/i)
        expect(firstNameInput).toHaveAccessibleDescription()
      })
    })

    // SKIPPED: terms checkbox is on step 2 of multi-step flow.
    it.skip('should have accessible terms checkbox', () => {
      renderRegisterPage()

      const checkbox = screen.getByRole('checkbox', { name: /I agree to the Terms/i })
      expect(checkbox).toBeInTheDocument()
      expect(checkbox).toHaveAccessibleName()
    })
  })

  // SKIPPED: optional phone field moved to step 2 of multi-step flow.
  describe.skip('Optional Fields', () => {
    it('should allow registration with optional phone number', async () => {
      const user = userEvent.setup()
      mockRegister.mockResolvedValue(mockUser)

      renderRegisterPage()

      await user.type(screen.getByLabelText(/First Name/i), 'Test')
      await user.type(screen.getByLabelText(/Last Name/i), 'User')
      await user.type(screen.getByLabelText(/Email Address/i), 'test@example.com')

      const phoneInput = screen.queryByLabelText(/Phone/i)
      if (phoneInput) {
        await user.type(phoneInput, '123-456-7890')
      }

      await user.type(screen.getByLabelText(/Create a Password/i), 'Secur3Pass!')
      await user.type(screen.getByLabelText(/Confirm.*Password/i), 'Secur3Pass!')
      await user.click(screen.getByRole('checkbox', { name: /I agree to the Terms/i }))

      await user.click(screen.getByRole('button', { name: /Create Account/i }))

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalled()
      })
    })
  })
})
