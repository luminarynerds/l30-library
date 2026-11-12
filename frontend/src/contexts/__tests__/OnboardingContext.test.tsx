/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { OnboardingProvider, useOnboarding } from '../OnboardingContext'

// Override the global AuthContext mock so we can present an authenticated patron.
const mockUseAuth = vi.fn()
vi.mock('@/contexts/AuthContext', () => ({
  __esModule: true,
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: () => mockUseAuth(),
  default: { useAuth: () => mockUseAuth() },
}))

// Mock the patron onboarding API.
const mockGetStatus = vi.fn()
vi.mock('@/api/domains/patron/patron-onboarding-api', () => ({
  patronOnboardingApi: {
    getStatus: () => mockGetStatus(),
  },
}))

function ProbeComponent() {
  const ctx = useOnboarding()
  return (
    <div>
      <span data-testid="completed">{String(ctx.welcomeWizardCompleted)}</span>
      <span data-testid="skipped">{String(ctx.welcomeWizardSkipped)}</span>
      <span data-testid="show">{String(ctx.showWelcomeWizard)}</span>
      <span data-testid="should-show-patron">{String(ctx.shouldShowPatronOnboarding)}</span>
      <span data-testid="current-step">{String(ctx.currentStep)}</span>
    </div>
  )
}

function renderWithProviders(): ReturnType<typeof render> {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <OnboardingProvider>
        <ProbeComponent />
      </OnboardingProvider>
    </QueryClientProvider>
  )
}

describe('OnboardingContext server hydration', () => {
  beforeEach(() => {
    // Wipe localStorage between tests so we exercise the "empty cache" path.
    window.localStorage.clear()
    mockUseAuth.mockReset()
    mockGetStatus.mockReset()
  })

  it('flips welcomeWizardCompleted=true when server reports completion, even with empty localStorage', async () => {
    // Simulates the cross-device case: patron finished onboarding on device A,
    // arrives on device B with no localStorage.
    mockUseAuth.mockReturnValue({
      user: { id: 1, role: 'patron', onboarding_completed_at: null },
      isAuthenticated: true,
    })
    mockGetStatus.mockResolvedValue({
      patron_id: 1,
      current_step: 5,
      step_welcome_completed: true,
      step_preferences_completed: true,
      step_branch_completed: true,
      step_tour_completed: true,
      step_complete_completed: true,
      skipped: false,
      completed_at: '2026-05-19T10:00:00Z',
      started_at: '2026-05-19T09:50:00Z',
    })

    const { getByTestId } = renderWithProviders()

    await waitFor(() => {
      expect(getByTestId('completed').textContent).toBe('true')
    })
    expect(getByTestId('show').textContent).toBe('false')
    expect(getByTestId('should-show-patron').textContent).toBe('false')
  })

  it('hydrates currentStep from the server for an in-progress patron', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 2, role: 'patron', onboarding_completed_at: null },
      isAuthenticated: true,
    })
    mockGetStatus.mockResolvedValue({
      patron_id: 2,
      current_step: 3,
      step_welcome_completed: true,
      step_preferences_completed: true,
      step_branch_completed: false,
      step_tour_completed: false,
      step_complete_completed: false,
      skipped: false,
      completed_at: null,
      started_at: '2026-05-19T09:00:00Z',
    })

    const { getByTestId } = renderWithProviders()

    await waitFor(() => {
      expect(getByTestId('current-step').textContent).toBe('3')
    })
    expect(getByTestId('completed').textContent).toBe('false')
    expect(getByTestId('show').textContent).toBe('true')
    expect(getByTestId('should-show-patron').textContent).toBe('true')
  })

  it('respects the server "skipped" flag', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 3, role: 'patron', onboarding_completed_at: null },
      isAuthenticated: true,
    })
    mockGetStatus.mockResolvedValue({
      patron_id: 3,
      current_step: 2,
      step_welcome_completed: true,
      step_preferences_completed: false,
      step_branch_completed: false,
      step_tour_completed: false,
      step_complete_completed: false,
      skipped: true,
      completed_at: null,
      started_at: '2026-05-19T09:00:00Z',
    })

    const { getByTestId } = renderWithProviders()

    await waitFor(() => {
      expect(getByTestId('skipped').textContent).toBe('true')
    })
    expect(getByTestId('show').textContent).toBe('false')
    expect(getByTestId('should-show-patron').textContent).toBe('false')
  })

  it('does not call the patron status endpoint for staff users', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 4, role: 'librarian', onboarding_completed_at: null },
      isAuthenticated: true,
    })

    renderWithProviders()

    // Wait a tick to allow useQuery enabled-gating to settle, then assert no call.
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0))
    })
    expect(mockGetStatus).not.toHaveBeenCalled()
  })

  it('falls back to local state when the server call fails', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 5, role: 'patron', onboarding_completed_at: null },
      isAuthenticated: true,
    })
    mockGetStatus.mockRejectedValue(new Error('network'))

    const { getByTestId } = renderWithProviders()

    // Default initial state: showWelcomeWizard=true, completed=false.
    await waitFor(() => {
      expect(getByTestId('show').textContent).toBe('true')
    })
    expect(getByTestId('completed').textContent).toBe('false')
  })
})
