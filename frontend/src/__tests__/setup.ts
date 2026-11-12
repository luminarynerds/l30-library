/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { vi, expect } from "vitest"

// Mock window.matchMedia before other imports
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver (not available in jsdom)
class MockIntersectionObserver {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
  constructor(callback: IntersectionObserverCallback) {
    // Immediately trigger with isIntersecting: true so elements become visible
    setTimeout(() => {
      callback(
        [{ isIntersecting: true, target: document.createElement('div') } as unknown as IntersectionObserverEntry],
        this as unknown as IntersectionObserver,
      )
    }, 0)
  }
}
Object.defineProperty(window, 'IntersectionObserver', { value: MockIntersectionObserver })

// Mock localStorage before other imports
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, "localStorage", { value: localStorageMock })

// Mock fetch globally before other imports
global.fetch = vi.fn()

// Mock organization features API so the real OrganizationFeaturesProvider
// used in test-utils resolves with defaults instead of hanging on a real fetch.
vi.mock("@/api/organization-features-api", () => ({
  getOrganizationFeatures: vi.fn().mockResolvedValue({}),
}))
vi.mock("../../api/organization-features-api", () => ({
  getOrganizationFeatures: vi.fn().mockResolvedValue({}),
}))

// Global AuthContext mock. Individual tests can override per-test via
// `vi.mock('@/contexts/AuthContext', ...)` at the top of their file.
vi.mock("@/contexts/AuthContext", async () => {
  const React = await import("react")
  const defaultAuth = {
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
  }
  return {
    AuthProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
    useAuth: () => defaultAuth,
    default: defaultAuth,
  }
})

// Now import testing libraries that depend on mocks
import "@testing-library/jest-dom"
import { toHaveNoViolations } from "jest-axe"

// Preload English translations once for the whole suite so individual tests
// no longer need to call loadLanguage('en'). Top-level await is supported in
// vitest setup files. Without this, components that render before a test's
// own loadLanguage promise resolves leak raw dotted keys into assertions.
import { loadLanguage } from "@/i18n/translations"
await loadLanguage("en")

// Extend Vitest expect with jest-axe matchers
expect.extend(toHaveNoViolations)

// Augment Vitest types to include jest-axe matchers
declare module "vitest" {
  interface Assertion {
    toHaveNoViolations(): void
  }
}
