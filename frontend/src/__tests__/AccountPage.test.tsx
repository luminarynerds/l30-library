/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "./utils/test-utils"
import userEvent from "@testing-library/user-event"
import { BrowserRouter, MemoryRouter } from "react-router-dom"
import { ReactNode } from "react"
import AccountPage from "../pages/AccountPage"
import { AuthProvider } from "../contexts/AuthContext"
import { useAuth } from "@/contexts/AuthContext"
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'

vi.mock('@/contexts/OrganizationFeaturesContext', async () => {
  const actual = await vi.importActual<typeof import('@/contexts/OrganizationFeaturesContext')>(
    '@/contexts/OrganizationFeaturesContext'
  )
  return {
    ...actual,
    // Default: all flags on, no items culled. Per-test calls override with
    // `vi.mocked(useOrganizationFeatures).mockReturnValue(...)`. Keeping a
    // working default here prevents existing authenticated tests from
    // crashing on `undefined` once AccountPage starts calling the hook.
    useOrganizationFeatures: vi.fn(() => ({
      features: {} as any,
      loading: false,
      isFeatureEnabled: () => true,
      refresh: vi.fn(),
      refetch: vi.fn(),
    })),
  }
})

// Override the global AuthContext mock (setup.ts) so this file can drive
// authentication state per-test. The default still returns unauthenticated
// so the existing tests continue to see the AuthForm.
vi.mock("@/contexts/AuthContext", async () => {
  const React = await import("react")
  return {
    AuthProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
    useAuth: vi.fn(() => ({
      user: null,
      token: null,
      isLoading: false,
      isAuthenticated: false,
      sessionExpired: false,
      clearSessionExpired: vi.fn(),
      login: vi.fn().mockResolvedValue(undefined),
      register: vi.fn().mockResolvedValue(null),
      logout: vi.fn().mockResolvedValue(undefined),
      updateProfile: vi.fn().mockResolvedValue(undefined),
      refreshUser: vi.fn().mockResolvedValue(undefined),
      showTimeoutWarning: false,
      timeoutSeconds: 120,
      dismissTimeoutWarning: vi.fn(),
      extendSession: vi.fn(),
      getSessionDuration: vi.fn(() => null),
    })),
  }
})

// Mock FamilyOverview so this test stays scoped to AccountPage routing;
// FamilyOverview internals are exercised by its own tests.
vi.mock("../components/account/FamilyOverview", () => ({
  FamilyOverview: () => <h2>Family Account</h2>,
}))


// Mock the API module
vi.mock("../api/api", () => ({
  getMyCheckouts: vi.fn().mockResolvedValue([]),
  getMyHolds: vi.fn().mockResolvedValue([]),
  getMyHistory: vi.fn().mockResolvedValue([]),
  getMyFinesSummary: vi.fn().mockResolvedValue({ total_outstanding: 0, total_paid: 0, outstanding_count: 0, paid_count: 0 }),
  getMyFavorites: vi.fn().mockResolvedValue([]),
  getMyLists: vi.fn().mockResolvedValue([]),
  renewCheckout: vi.fn(),
  cancelHold: vi.fn(),
  removeFavorite: vi.fn(),
  deleteList: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  getMe: vi.fn().mockResolvedValue(null),
  updateMe: vi.fn(),
  refreshAccessToken: vi.fn(),
}))

// Mock react-hot-toast
vi.mock("react-hot-toast", () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

// Create a wrapper with all providers
const AllProviders = ({ children }: { children: ReactNode }) => (
  <BrowserRouter>
    <AuthProvider>{children}</AuthProvider>
  </BrowserRouter>
)

const renderWithProviders = (ui: React.ReactElement) => {
  return render(<AllProviders>{ui}</AllProviders>)
}

describe("AccountPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Clear localStorage mock
    vi.mocked(window.localStorage.getItem).mockReturnValue(null)
    vi.mocked(window.localStorage.setItem).mockClear()
    vi.mocked(window.localStorage.removeItem).mockClear()
  })

  describe("When not authenticated", () => {
    it("should render Sign In heading", async () => {
      renderWithProviders(<AccountPage />)

      await waitFor(() => {
        expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument()
      })
    })

    it("should render sign in button in form", async () => {
      renderWithProviders(<AccountPage />)

      await waitFor(() => {
        const submitButton = screen.getByRole("button", { name: /sign in/i })
        expect(submitButton).toBeInTheDocument()
      })
    })

    it("should render sign up link", async () => {
      renderWithProviders(<AccountPage />)

      await waitFor(() => {
        expect(screen.getByText(/don't have an account\? sign up/i)).toBeInTheDocument()
      })
    })

    it("should show email input in login form", async () => {
      renderWithProviders(<AccountPage />)

      await waitFor(() => {
        const emailInput = screen.getByPlaceholderText(/your@email.com/i)
        expect(emailInput).toBeInTheDocument()
        expect(emailInput).toHaveAttribute("type", "email")
      })
    })

    it("should show password input in login form", async () => {
      renderWithProviders(<AccountPage />)

      await waitFor(() => {
        const passwordInputs = document.querySelectorAll("input[type=password]")
        expect(passwordInputs.length).toBeGreaterThan(0)
      })
    })

    it("should switch to register form when clicking sign up link", async () => {
      const user = userEvent.setup()
      renderWithProviders(<AccountPage />)

      await waitFor(() => {
        expect(screen.getByText(/don't have an account\? sign up/i)).toBeInTheDocument()
      })

      const signUpLink = screen.getByText(/don't have an account\? sign up/i)
      await user.click(signUpLink)

      await waitFor(() => {
        expect(screen.getByRole("heading", { name: /create account/i })).toBeInTheDocument()
      })
    })

    it("should show name fields in register form", async () => {
      const user = userEvent.setup()
      renderWithProviders(<AccountPage />)

      await waitFor(() => {
        expect(screen.getByText(/don't have an account\? sign up/i)).toBeInTheDocument()
      })

      const signUpLink = screen.getByText(/don't have an account\? sign up/i)
      await user.click(signUpLink)

      // Register form exposes a First Name field in the current UI.
      await waitFor(() => {
        expect(screen.getByText(/first name/i)).toBeInTheDocument()
      })
    })

    it("should require email field", async () => {
      renderWithProviders(<AccountPage />)

      await waitFor(() => {
        const emailInput = screen.getByPlaceholderText(/your@email.com/i)
        expect(emailInput).toHaveAttribute("required")
      })
    })
  })

  describe("Form validation", () => {
    it("should have email input with correct type", async () => {
      renderWithProviders(<AccountPage />)

      await waitFor(() => {
        const emailInput = screen.getByPlaceholderText(/your@email.com/i)
        expect(emailInput).toHaveAttribute("type", "email")
      })
    })

    it("should have submit button with type submit", async () => {
      renderWithProviders(<AccountPage />)

      await waitFor(() => {
        const submitButtons = document.querySelectorAll("button[type=submit]")
        expect(submitButtons.length).toBe(1)
      })
    })
  })

  describe("UI Elements", () => {
    it("should render a heading", async () => {
      renderWithProviders(<AccountPage />)

      await waitFor(() => {
        expect(screen.getByRole("heading", { level: 2 })).toBeInTheDocument()
      })
    })

    it("should show toggle link to switch between login and register", async () => {
      renderWithProviders(<AccountPage />)

      await waitFor(() => {
        expect(screen.getByText(/don't have an account\? sign up/i)).toBeInTheDocument()
      })
    })
  })

  describe("Mode switching", () => {
    it("should switch between login and register modes", async () => {
      const user = userEvent.setup()
      renderWithProviders(<AccountPage />)

      // Initially should show Sign In
      await waitFor(() => {
        expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument()
      })

      // Click sign up link
      const signUpLink = screen.getByText(/don't have an account\? sign up/i)
      await user.click(signUpLink)

      // Should now show Create Account
      await waitFor(() => {
        expect(screen.getByRole("heading", { name: /create account/i })).toBeInTheDocument()
      })

      // Click sign in link to go back
      const signInLink = screen.getByText(/already have an account\? sign in/i)
      await user.click(signInLink)

      // Should be back to Sign In
      await waitFor(() => {
        expect(screen.getByRole("heading", { name: /sign in/i })).toBeInTheDocument()
      })
    })
  })

  it("renders the Family tab content when ?tab=family is in the URL", async () => {
    const mockUser = {
      id: 1,
      email: "test@example.com",
      first_name: "Test",
      last_name: "User",
      role: "patron" as const,
      is_active: true,
      library_card: "LSC000001",
      phone: null,
      address: null,
      email_verified: true,
      track_reading_history: true,
      created_at: new Date().toISOString(),
      onboarding_completed_at: new Date().toISOString(),
      onboarding_skipped: false,
      home_branch_id: null,
    }
    vi.mocked(useAuth).mockReturnValue({
      user: mockUser,
      token: "fake-access-token",
      isLoading: false,
      isAuthenticated: true,
      sessionExpired: false,
      clearSessionExpired: vi.fn(),
      login: vi.fn().mockResolvedValue(undefined),
      register: vi.fn().mockResolvedValue(null),
      logout: vi.fn().mockResolvedValue(undefined),
      updateProfile: vi.fn().mockResolvedValue(undefined),
      refreshUser: vi.fn().mockResolvedValue(undefined),
      showTimeoutWarning: false,
      timeoutSeconds: 120,
      dismissTimeoutWarning: vi.fn(),
      extendSession: vi.fn(),
      getSessionDuration: vi.fn(() => null),
    } as unknown as ReturnType<typeof useAuth>)

    render(
      <MemoryRouter initialEntries={["/account?tab=family"]}>
        <AuthProvider>
          <AccountPage />
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(
      () => {
        expect(screen.getByRole("heading", { name: /family account/i })).toBeInTheDocument()
      },
      { timeout: 3000 }
    )
  })
})

const featuresAllOn = {
  features: { volunteers_enabled: true, events_enabled: true, family_card_enabled: true, indie_platform_enabled: true, notifications_enabled: true },
  loading: false,
  isFeatureEnabled: (_k: string) => true,
  refresh: vi.fn(),
  refetch: vi.fn(),
}

const featuresVolunteerOff = {
  ...featuresAllOn,
  features: { ...featuresAllOn.features, volunteers_enabled: false },
  isFeatureEnabled: (k: string) => k !== 'volunteers_enabled',
}

describe('AccountPage flag cascade', () => {
  beforeEach(() => {
    // Provide an authenticated user for these tests (the existing setup
    // mocks useAuth as unauthenticated by default).
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 1, first_name: 'Test', last_name: 'Patron', email: 't@x', role: 'patron', indie_author: false, library_card: '0001' } as any,
      token: 'tok',
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
      timeoutSeconds: 0,
      dismissTimeoutWarning: vi.fn(),
      extendSession: vi.fn(),
      getSessionDuration: vi.fn(() => null),
    } as any)
  })

  it('hides the Volunteer tab when volunteers_enabled is false', async () => {
    vi.mocked(useOrganizationFeatures).mockReturnValue(featuresVolunteerOff as any)

    render(
      <BrowserRouter>
        <AccountPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /volunteer/i })).not.toBeInTheDocument()
    })
  })

  it('falls activeTab back to overview when the active flag flips off', async () => {
    vi.mocked(useOrganizationFeatures).mockReturnValue(featuresAllOn as any)

    const { rerender } = render(
      <MemoryRouter initialEntries={['/account?tab=volunteer']}>
        <AccountPage />
      </MemoryRouter>
    )

    // Volunteer tab renders in both mobile pill nav and desktop sidebar — both
    // should be aria-current when active.
    await waitFor(() => {
      const volunteerButtons = screen.getAllByRole('button', { name: /volunteer/i })
      expect(volunteerButtons.length).toBeGreaterThan(0)
      volunteerButtons.forEach(btn => expect(btn).toHaveAttribute('aria-current', 'page'))
    })

    // Flag flips off mid-session.
    vi.mocked(useOrganizationFeatures).mockReturnValue(featuresVolunteerOff as any)
    rerender(
      <MemoryRouter initialEntries={['/account?tab=volunteer']}>
        <AccountPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      const overviewButtons = screen.getAllByRole('button', { name: /overview/i })
      expect(overviewButtons.length).toBeGreaterThan(0)
      overviewButtons.forEach(btn => expect(btn).toHaveAttribute('aria-current', 'page'))
    })
  })

  it('does not mount the volunteer panel when ?tab=volunteer is bookmarked but volunteers_enabled is false', async () => {
    vi.mocked(useOrganizationFeatures).mockReturnValue(featuresVolunteerOff as any)

    render(
      <MemoryRouter initialEntries={['/account?tab=volunteer']}>
        <AccountPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      const overviewButtons = screen.getAllByRole('button', { name: /overview/i })
      expect(overviewButtons.length).toBeGreaterThan(0)
      overviewButtons.forEach(b => expect(b).toHaveAttribute('aria-current', 'page'))
      expect(screen.queryByRole('button', { name: /volunteer/i })).not.toBeInTheDocument()
    })
  })

  it('keeps the "My Library" heading when a flagged item drops but unflagged items remain', async () => {
    // Confirm at least one tab in My Library is always-on (e.g. checkouts),
    // so this test asserts that flag-only items leave the heading + unflagged
    // items intact. The stronger "drop the heading" case requires every item
    // in the section to be flagged off, which isn't currently achievable for
    // the My Library section (checkouts/holds/overview are unflagged) —
    // assert instead that the volunteer item drops while the heading stays.
    vi.mocked(useOrganizationFeatures).mockReturnValue(featuresVolunteerOff as any)

    render(
      <BrowserRouter>
        <AccountPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/my library/i)).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /volunteer/i })).not.toBeInTheDocument()
    })
  })
})
