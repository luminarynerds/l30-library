/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrandingProvider } from '../../contexts/BrandingContext'
import { OrganizationFeaturesProvider } from '../../contexts/OrganizationFeaturesContext'
import LoginPage from '../LoginPage'

const mockLogin = vi.fn()
const mockClearSessionExpired = vi.fn()
const mockNavigate = vi.fn()
const mockRequestMagicLink = vi.fn()

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    login: mockLogin,
    isAuthenticated: false,
    sessionExpired: false,
    clearSessionExpired: mockClearSessionExpired,
  }),
}))

// LoginPage's magic-link tab calls the dedicated requestMagicLink endpoint
// (not forgotPassword, which backs the separate "Forgot password?" link).
vi.mock('../../api/api', () => ({
  requestMagicLink: (...args: unknown[]) => mockRequestMagicLink(...args),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('../../i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'auth.welcomeBack': 'Welcome back',
        'auth.signInToAccount': 'Sign in to your account',
        'auth.email': 'Email',
        'auth.libraryCard': 'Library Card',
        'auth.emailAddress': 'Email address',
        'auth.emailPlaceholder': 'you@example.com',
        'auth.password': 'Password',
        'auth.enterPassword': 'Enter password',
        'auth.loginButton': 'Sign In',
        'auth.signingIn': 'Signing in...',
        'auth.genericLoginError': 'Login failed',
        'auth.dontHaveAccount': "Don't have an account?",
        'auth.createAccountNow': 'Create account now',
        'auth.forgotPassword': 'Forgot password?',
        'auth.needHelp': 'Need help?',
        'auth.contactUs': 'Contact us',
        'auth.magicLink': 'Magic Link',
        'auth.magicLinkDescription':
          "We'll email a one-time sign-in link so you can access your account securely without your password.",
        'auth.magicLinkSent': 'Check your inbox for a magic sign-in link',
        'auth.sendMagicLink': 'Send magic link',
      }
      return translations[key] || key
    },
  }),
}))

function renderLoginPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <QueryClientProvider client={queryClient}>
        <BrandingProvider>
          <OrganizationFeaturesProvider>
            <LoginPage />
          </OrganizationFeaturesProvider>
        </BrandingProvider>
      </QueryClientProvider>
    </MemoryRouter>
  )
}

describe('LoginPage magic link', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows a magic link tab and sends a magic-link request', async () => {
    const user = userEvent.setup()
    mockRequestMagicLink.mockResolvedValue({ message: 'sent' })

    renderLoginPage()
    await user.click(screen.getByRole('tab', { name: /magic link/i }))
    await user.type(screen.getByLabelText(/email address/i), 'reader@example.com')
    await user.click(screen.getByRole('button', { name: /send magic link/i }))

    await waitFor(() => {
      // Turnstile has no site key configured in tests, so TurnstileWidget
      // dev-bypasses with a fixed token (see TurnstileWidget.tsx).
      expect(mockRequestMagicLink).toHaveBeenCalledWith('reader@example.com', 'dev-bypass')
    })

    expect(screen.getByText(/check your inbox for a magic sign-in link/i)).toBeInTheDocument()
    expect(mockLogin).not.toHaveBeenCalled()
  })
})
