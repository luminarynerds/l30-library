/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for PreferencesContext
 *
 * Tests for:
 * - Optimistic update rollback on API failure
 * - Preference persistence
 * - Theme application
 */
/// <reference types="@testing-library/jest-dom/vitest" />

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render } from "@testing-library/react"
import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ReactNode } from "react"
import { PreferencesProvider, usePreferences, UserPreferences } from "../../contexts/PreferencesContext"
import { BrowserRouter } from "react-router-dom"
import { UnifiedAccessibilityProvider } from "../../features/accessibility/context/UnifiedAccessibilityContext"
import { I18nProvider } from "../../i18n/I18nContext"
import { BrandingProvider } from "../../contexts/BrandingContext"

// Mock the API module
const mockApiGet = vi.fn()
const mockApiPut = vi.fn()

vi.mock("../../api/api", () => ({
  default: {
    get: (...args: unknown[]) => mockApiGet(...args),
    put: (...args: unknown[]) => mockApiPut(...args),
    post: vi.fn().mockResolvedValue({ data: null }),
    delete: vi.fn().mockResolvedValue({ data: null }),
  },
  getMe: vi.fn().mockResolvedValue(null),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  updateMe: vi.fn(),
  refreshAccessToken: vi.fn(),
}))

// Mock AuthContext to simulate authenticated state
vi.mock("../../contexts/AuthContext", async () => {
  const actual = await vi.importActual("../../contexts/AuthContext")
  return {
    ...actual,
    useAuth: vi.fn(() => ({
      isAuthenticated: true,
      user: { id: 1, email: "test@example.com" },
      login: vi.fn(),
      logout: vi.fn(),
      isLoading: false,
    })),
  }
})

// Test component that exposes preferences context
function TestConsumer({ onUpdate }: { onUpdate?: (prefs: UserPreferences) => void }) {
  const { preferences, updatePreferences, loading } = usePreferences()

  return (
    <div>
      <div data-testid="theme">{preferences.theme}</div>
      <div data-testid="font-size">{preferences.font_size}</div>
      <div data-testid="dyslexia-font">{preferences.dyslexia_font ? "true" : "false"}</div>
      <div data-testid="loading">{loading ? "loading" : "ready"}</div>
      <button
        data-testid="toggle-dyslexia"
        onClick={async () => {
          try {
            await updatePreferences({ dyslexia_font: !preferences.dyslexia_font })
            onUpdate?.(preferences)
          } catch {
            // Error handled
          }
        }}
      >
        Toggle Dyslexia Font
      </button>
      <button
        data-testid="change-theme"
        onClick={async () => {
          try {
            await updatePreferences({ theme: "dark" })
            onUpdate?.(preferences)
          } catch {
            // Error handled
          }
        }}
      >
        Set Dark Theme
      </button>
    </div>
  )
}

// Consumer that does NOT swallow errors, so a rejected updatePreferences
// surfaces as an unhandled rejection (the bug we are fixing). onSettled is
// called with "resolved" or "rejected" so the test can assert which happened.
function UnhandledRejectionConsumer({ onSettled }: { onSettled: (outcome: string) => void }) {
  const { preferences, updatePreferences } = usePreferences()

  return (
    <div>
      <div data-testid="theme">{preferences.theme}</div>
      <button
        data-testid="change-theme-nocatch"
        onClick={() =>
          updatePreferences({ theme: "dark" }).then(
            () => onSettled("resolved"),
            () => onSettled("rejected")
          )
        }
      >
        Set Dark Theme (no catch)
      </button>
    </div>
  )
}

// Wrapper with all providers
function AllProviders({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter>
      <BrandingProvider>
        <I18nProvider>
          <UnifiedAccessibilityProvider>
            <PreferencesProvider>
              {children}
            </PreferencesProvider>
          </UnifiedAccessibilityProvider>
        </I18nProvider>
      </BrandingProvider>
    </BrowserRouter>
  )
}

describe("PreferencesContext", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Clear localStorage
    vi.mocked(window.localStorage.getItem).mockReturnValue(null)
    vi.mocked(window.localStorage.setItem).mockClear()
    vi.mocked(window.localStorage.removeItem).mockClear()

    // Default successful API responses
    mockApiGet.mockResolvedValue({
      id: 1,
      user_id: 1,
      theme: "system",
      font_size: "medium",
      dyslexia_font: false,
      reduced_motion: false,
      high_contrast: false,
      focus_mode: "balanced",
      hide_streaks: false,
      hide_gamification: false,
      preferred_content_variant: "default",
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe("Optimistic Updates", () => {
    it("should apply optimistic update immediately", async () => {
      const user = userEvent.setup()

      // Mock successful API call
      mockApiPut.mockResolvedValue({
        id: 1,
        user_id: 1,
        theme: "system",
        font_size: "medium",
        dyslexia_font: true, // Updated value
        reduced_motion: false,
        high_contrast: false,
        focus_mode: "balanced",
        hide_streaks: false,
        hide_gamification: false,
        preferred_content_variant: "default",
      })

      render(
        <AllProviders>
          <TestConsumer />
        </AllProviders>
      )

      // Initial state
      await waitFor(() => {
        expect(screen.getByTestId("dyslexia-font")).toHaveTextContent("false")
      })

      // Click toggle
      await user.click(screen.getByTestId("toggle-dyslexia"))

      // Should update immediately (optimistic)
      await waitFor(() => {
        expect(screen.getByTestId("dyslexia-font")).toHaveTextContent("true")
      })
    })

    it("should rollback optimistic update on API failure", async () => {
      const user = userEvent.setup()

      // Mock API failure
      mockApiPut.mockRejectedValue(new Error("Network error"))

      render(
        <AllProviders>
          <TestConsumer />
        </AllProviders>
      )

      // Initial state
      await waitFor(() => {
        expect(screen.getByTestId("dyslexia-font")).toHaveTextContent("false")
      })

      // Click toggle
      await user.click(screen.getByTestId("toggle-dyslexia"))

      // After API fails, should rollback to original value
      await waitFor(() => {
        expect(screen.getByTestId("dyslexia-font")).toHaveTextContent("false")
      }, { timeout: 2000 })
    })

    it("should rollback theme change on API failure", async () => {
      const user = userEvent.setup()

      // Mock API failure
      mockApiPut.mockRejectedValue(new Error("Server error"))

      render(
        <AllProviders>
          <TestConsumer />
        </AllProviders>
      )

      // Initial state
      await waitFor(() => {
        expect(screen.getByTestId("theme")).toHaveTextContent("system")
      })

      // Click to change theme
      await user.click(screen.getByTestId("change-theme"))

      // Should rollback to original theme
      await waitFor(() => {
        expect(screen.getByTestId("theme")).toHaveTextContent("system")
      }, { timeout: 2000 })
    })
  })

  describe("Preference Loading", () => {
    it("should load preferences from API on mount", async () => {
      mockApiGet.mockResolvedValue({
        id: 1,
        user_id: 1,
        theme: "dark",
        font_size: "large",
        dyslexia_font: true,
        reduced_motion: true,
        high_contrast: false,
        focus_mode: "deep_dive",
        hide_streaks: false,
        hide_gamification: false,
        preferred_content_variant: "default",
      })

      render(
        <AllProviders>
          <TestConsumer />
        </AllProviders>
      )

      await waitFor(() => {
        expect(screen.getByTestId("theme")).toHaveTextContent("dark")
        expect(screen.getByTestId("font-size")).toHaveTextContent("large")
        expect(screen.getByTestId("dyslexia-font")).toHaveTextContent("true")
      })
    })

    it("should use localStorage preferences when API fails", async () => {
      // Mock localStorage to return saved preferences
      vi.mocked(window.localStorage.getItem).mockReturnValue(
        JSON.stringify({
          theme: "light",
          font_size: "small",
          dyslexia_font: true,
        })
      )

      // Mock API failure
      mockApiGet.mockRejectedValue(new Error("API unavailable"))

      render(
        <AllProviders>
          <TestConsumer />
        </AllProviders>
      )

      // Should use localStorage values
      await waitFor(() => {
        expect(screen.getByTestId("theme")).toHaveTextContent("light")
      })
    })

    it("should keep existing preferences when the endpoint 404s (feature disabled), not wipe them", async () => {
      // Staff loads a page with the learning platform feature turned OFF.
      vi.mocked(window.localStorage.getItem).mockReturnValue(
        JSON.stringify({
          theme: "dark",
          font_size: "large",
        })
      )

      // Endpoint returns 404 "feature not enabled"
      const featureDisabled = Object.assign(
        new Error("Learning platform feature is not enabled"),
        { status: 404 }
      )
      mockApiGet.mockRejectedValue(featureDisabled)

      render(
        <AllProviders>
          <TestConsumer />
        </AllProviders>
      )

      // Wait for the refresh effect to settle...
      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("ready")
      })

      // ...and the stored prefs must NOT have been clobbered to empty.
      expect(screen.getByTestId("theme")).toHaveTextContent("dark")
      expect(screen.getByTestId("font-size")).toHaveTextContent("large")
    })
  })

  describe("Feature-flag-disabled (404) degradation", () => {
    it("should keep the optimistic value and not reject when the save 404s", async () => {
      const user = userEvent.setup()

      // PUT to a disabled feature endpoint returns 404
      const featureDisabled = Object.assign(
        new Error("Learning platform feature is not enabled"),
        { status: 404 }
      )
      mockApiPut.mockRejectedValue(featureDisabled)

      const onUpdate = vi.fn()
      render(
        <AllProviders>
          <UnhandledRejectionConsumer onSettled={onUpdate} />
        </AllProviders>
      )

      await waitFor(() => {
        expect(screen.getByTestId("theme")).toHaveTextContent("system")
      })

      await user.click(screen.getByTestId("change-theme-nocatch"))

      // The optimistic value sticks (works locally via localStorage); no rollback.
      await waitFor(() => {
        expect(screen.getByTestId("theme")).toHaveTextContent("dark")
      })
      // updatePreferences resolved rather than rejecting.
      await waitFor(() => {
        expect(onUpdate).toHaveBeenCalledWith("resolved")
      })
    })
  })

  describe("localStorage Persistence", () => {
    it("should save preferences to localStorage on update", async () => {
      const user = userEvent.setup()

      mockApiPut.mockResolvedValue({
        id: 1,
        user_id: 1,
        theme: "dark",
        font_size: "medium",
        dyslexia_font: false,
        reduced_motion: false,
        high_contrast: false,
        focus_mode: "balanced",
        hide_streaks: false,
        hide_gamification: false,
        preferred_content_variant: "default",
      })

      render(
        <AllProviders>
          <TestConsumer />
        </AllProviders>
      )

      await waitFor(() => {
        expect(screen.getByTestId("loading")).toHaveTextContent("ready")
      })

      await user.click(screen.getByTestId("change-theme"))

      await waitFor(() => {
        expect(window.localStorage.setItem).toHaveBeenCalled()
      })
    })
  })

  describe("Default Values", () => {
    it("should use default values when no preferences exist", async () => {
      // Mock no localStorage and API returns empty
      vi.mocked(window.localStorage.getItem).mockReturnValue(null)
      mockApiGet.mockResolvedValue({
        id: 0,
        user_id: 0,
        theme: "system",
        font_size: "medium",
        dyslexia_font: false,
        reduced_motion: false,
        high_contrast: false,
        focus_mode: "balanced",
        hide_streaks: false,
        hide_gamification: false,
        preferred_content_variant: "default",
      })

      render(
        <AllProviders>
          <TestConsumer />
        </AllProviders>
      )

      await waitFor(() => {
        expect(screen.getByTestId("theme")).toHaveTextContent("system")
        expect(screen.getByTestId("font-size")).toHaveTextContent("medium")
        expect(screen.getByTestId("dyslexia-font")).toHaveTextContent("false")
      })
    })
  })
})
