/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
/**
 * Test Utilities
 *
 * Provides common test wrappers and utilities for rendering components
 * with all required providers (Router, Auth, Preferences, etc.)
 */

import { ReactElement, ReactNode } from "react"
import { render, RenderOptions } from "@testing-library/react"
import { MemoryRouter, MemoryRouterProps } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi } from "vitest"
import { createContext, useContext, useState, useCallback } from "react"
import type { User } from "../../api/domains/auth/auth-api"

interface RegisterData {
  email: string
  password: string
  first_name: string
  last_name: string
  full_name?: string
}

interface UpdateProfileData {
  first_name?: string
  last_name?: string
  full_name?: string
  phone?: string
  address?: string
}
import { UnifiedAccessibilityProvider } from "../../features/accessibility/context/UnifiedAccessibilityContext"
import { I18nProvider } from "../../i18n/I18nContext"
import { OrganizationFeaturesProvider } from "../../contexts/OrganizationFeaturesContext"
import { OnboardingProvider } from "../../contexts/OnboardingContext"
import { EssentialsModeProvider } from "../../contexts/EssentialsModeContext"
import { BrandingProvider } from "../../contexts/BrandingContext"

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  })
}

// ============================================================================
// Auth Context Implementation for Tests
// ============================================================================

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (credential: string, secret: string) => Promise<void>
  register: (data: RegisterData) => Promise<User>
  logout: () => Promise<void>
  updateProfile: (data: UpdateProfileData) => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

function TestAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const login = useCallback(async (credential: string, _secret: string) => {
    setIsLoading(true)
    // Mock login
    const mockUser = {
      id: 1,
      email: credential,
      first_name: "Test",
      last_name: "User",
      full_name: "Test User",
      role: "patron" as const,
      is_active: true,
      library_card: null,
      phone: "",
      address: null,
      pronouns: null,
      email_verified: true,
      track_reading_history: true,
      created_at: new Date().toISOString(),
      onboarding_completed_at: null,
      onboarding_skipped: false,
      home_branch_id: null,
      profile_image: null,
      preferred_language: "en",
    } satisfies User
    setUser(mockUser)
    setToken("mock-token-" + Date.now())
    setIsLoading(false)
  }, [])

  const logout = useCallback(async () => {
    setUser(null)
    setToken(null)
  }, [])

  const register = useCallback(async (data: RegisterData): Promise<User> => {
    const mockUser = {
      id: 1,
      email: data.email,
      first_name: data.first_name,
      last_name: data.last_name,
      full_name: data.full_name || "Test User",
      role: "patron" as const,
      is_active: true,
      library_card: null,
      phone: "",
      address: null,
      pronouns: null,
      email_verified: true,
      track_reading_history: true,
      created_at: new Date().toISOString(),
      onboarding_completed_at: null,
      onboarding_skipped: false,
      home_branch_id: null,
      profile_image: null,
      preferred_language: "en",
    }
    await login(data.email, data.password)
    return mockUser
  }, [login])

  const updateProfile = useCallback(async (data: UpdateProfileData) => {
    if (!user) throw new Error("Not authenticated")
    setUser({ ...user, ...data })
  }, [user])

  const refreshUser = useCallback(async () => {
    // Mock refresh - just keep existing state
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        updateProfile,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

// ============================================================================
// Preferences Context Implementation for Tests
// ============================================================================

export interface UserPreferences {
  id: number
  user_id: number
  theme: "light" | "dark" | "system"
  font_size: "small" | "medium" | "large"
  dyslexia_font: boolean
  reduced_motion: boolean
  high_contrast: boolean
  focus_mode: "balanced" | "quick_scan" | "deep_dive"
  hide_streaks: boolean
  hide_gamification: boolean
  preferred_content_variant: string
}

interface PreferencesContextType {
  preferences: UserPreferences
  loading: boolean
  updatePreferences: (updates: Partial<UserPreferences>) => Promise<void>
  refreshPreferences: () => Promise<void>
}

const defaultPreferences: UserPreferences = {
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
}

const PreferencesContext = createContext<PreferencesContextType>({
  preferences: defaultPreferences,
  loading: false,
  updatePreferences: async () => {},
  refreshPreferences: async () => {},
})

function TestPreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<UserPreferences>(() => {
    // Mock localStorage for tests
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("lsc-preferences")
      if (stored) {
        try {
          return { ...defaultPreferences, ...JSON.parse(stored) }
        } catch {
          return defaultPreferences
        }
      }
    }
    return defaultPreferences
  })
  const [loading, setLoading] = useState(false)

  const refreshPreferences = useCallback(async () => {
    // Mock refresh
    setLoading(false)
  }, [])

  const updatePreferences = useCallback(
    async (updates: Partial<UserPreferences>) => {
      const newPrefs = { ...preferences, ...updates }
      setPreferences(newPrefs)
      // Mock localStorage update
      if (typeof window !== "undefined") {
        localStorage.setItem("lsc-preferences", JSON.stringify(newPrefs))
      }
    },
    [preferences]
  )

  return (
    <PreferencesContext.Provider
      value={{ preferences, loading, updatePreferences, refreshPreferences }}
    >
      {children}
    </PreferencesContext.Provider>
  )
}

export function usePreferences(): PreferencesContextType {
  return useContext(PreferencesContext)
}

// ============================================================================
// Organization Features Context Implementation for Tests
// ============================================================================

export interface OrganizationFeatures {
  id: number
  gamification_enabled: boolean
  reading_programs_enabled: boolean
  board_features_enabled: boolean
  training_modules_enabled: boolean
  community_features_enabled: boolean
  email_notifications_enabled: boolean
  banned_books_tracking_enabled: boolean
  patron_portal_enabled: boolean
  self_checkout_enabled: boolean
  enabled_focus_modes: string[]
  enabled_themes: string[]
  enabled_fonts: string[]
  default_daily_goal_minutes: number
  max_holds_per_patron: number
  max_checkouts_per_patron: number
  configuration: Record<string, unknown> | null
  created_at: string
  updated_at: string | null
  updated_by_id: number | null
}

interface OrganizationFeaturesContextType {
  features: OrganizationFeatures | null
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
  isFeatureEnabled: (featureName: keyof OrganizationFeatures) => boolean
}

const OrganizationFeaturesContext = createContext<
  OrganizationFeaturesContextType | undefined
>(undefined)

export function useOrganizationFeatures(): OrganizationFeaturesContextType {
  const context = useContext(OrganizationFeaturesContext)
  if (!context) {
    throw new Error(
      "useOrganizationFeatures must be used within an OrganizationFeaturesProvider"
    )
  }
  return context
}

// ============================================================================
// Accessibility Context Implementation for Tests
// ============================================================================

interface AccessibilitySettings {
  language: string
  theme: string
  fontSize: number
  // Add other settings as needed
}

interface AccessibilityContextType {
  settings: AccessibilitySettings
  updateSetting: (key: string, value: string | number) => void
}

const AccessibilityContext = createContext<AccessibilityContextType | undefined>(
  undefined
)

function TestAccessibilityProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AccessibilitySettings>({
    language: "en",
    theme: "system",
    fontSize: 16,
  })

  const updateSetting = useCallback((key: string, value: string | number) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
  }, [])

  return (
    <AccessibilityContext.Provider value={{ settings, updateSetting }}>
      {children}
    </AccessibilityContext.Provider>
  )
}

export function useAccessibility(): AccessibilityContextType {
  const context = useContext(AccessibilityContext)
  if (!context) {
    throw new Error(
      "useAccessibility must be used within an AccessibilityProvider"
    )
  }
  return context
}

// ============================================================================
// All Providers Wrapper
// ============================================================================

interface AllProvidersProps {
  children: ReactNode
  routerProps?: MemoryRouterProps
  _routerProps?: MemoryRouterProps
}

function AllProviders({ children }: AllProvidersProps) {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <BrandingProvider>
      <I18nProvider>
        <UnifiedAccessibilityProvider>
          <TestAuthProvider>
            <TestPreferencesProvider>
              <TestAccessibilityProvider>
                <OrganizationFeaturesProvider>
                  <EssentialsModeProvider>
                    <OnboardingProvider>
                      {children}
                    </OnboardingProvider>
                  </EssentialsModeProvider>
                </OrganizationFeaturesProvider>
              </TestAccessibilityProvider>
            </TestPreferencesProvider>
          </TestAuthProvider>
        </UnifiedAccessibilityProvider>
      </I18nProvider>
      </BrandingProvider>
    </QueryClientProvider>
  )
}

interface CustomRenderOptions extends Omit<RenderOptions, "wrapper"> {
  routerProps?: MemoryRouterProps
}

function hasRouter(node: unknown, depth = 0): boolean {
  if (depth > 6 || node == null || typeof node !== "object") return false
  const element = node as { type?: unknown; props?: { children?: unknown } }
  const type = element.type as
    | { displayName?: string; name?: string }
    | string
    | undefined
  if (typeof type === "function" || typeof type === "object") {
    const t = type as { displayName?: string; name?: string }
    const name = t?.displayName || t?.name || ""
    if (/Router$/.test(name)) return true
  }
  const children = element.props?.children
  if (Array.isArray(children)) {
    return children.some((c) => hasRouter(c, depth + 1))
  }
  return hasRouter(children, depth + 1)
}

function customRender(ui: ReactElement, options?: CustomRenderOptions) {
  const { routerProps, ...renderOptions } = options || {}
  const alreadyRouted = hasRouter(ui)

  const wrapWithRouter = ({ children }: { children: ReactNode }) => (
    <MemoryRouter
      {...routerProps}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <AllProviders>{children}</AllProviders>
    </MemoryRouter>
  )

  const wrapWithoutRouter = ({ children }: { children: ReactNode }) => (
    <AllProviders>{children}</AllProviders>
  )

  if (alreadyRouted) {
    return render(ui, { wrapper: wrapWithoutRouter, ...renderOptions })
  }

  try {
    return render(ui, { wrapper: wrapWithRouter, ...renderOptions })
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    if (/cannot render a .*Router.* inside another .*Router/i.test(msg)) {
      return render(ui, { wrapper: wrapWithoutRouter, ...renderOptions })
    }
    throw err
  }
}

// Re-export everything from testing-library
export * from "@testing-library/react"
export { default as userEvent } from "@testing-library/user-event"
export { screen, waitFor, within } from "@testing-library/react"
export { customRender as render }

export function setupPageMocks() {
  // Mock API module
  vi.mock("../../api/api", () => ({
    default: {
      get: vi.fn().mockResolvedValue({ data: null }),
      post: vi.fn().mockResolvedValue({ data: null }),
      put: vi.fn().mockResolvedValue({ data: null }),
      delete: vi.fn().mockResolvedValue({ data: null }),
    },
    getMe: vi.fn().mockResolvedValue(null),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    updateMe: vi.fn(),
    refreshAccessToken: vi.fn(),
  }))

  // Mock localStorage
  const localStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
  }
  Object.defineProperty(window, "localStorage", {
    value: localStorageMock,
    writable: true,
  })
}

/**
 * List of public page routes for testing
 */
export const PUBLIC_PAGE_ROUTES = [
  { path: "/", name: "HomePage" },
  { path: "/catalog", name: "CatalogPage" },
  { path: "/events", name: "EventsPage" },
  { path: "/programs", name: "ReadingProgramsPage" },
  { path: "/releases", name: "ReleaseRadarPage" },
  { path: "/digital", name: "DigitalResourcesPage" },
  { path: "/ai", name: "AIToolsPage" },
  { path: "/business", name: "BusinessResourcesPage" },
  { path: "/legal", name: "LegalResourcesPage" },
  { path: "/community", name: "CommunityResourcesPage" },
  { path: "/about", name: "AboutUsPage" },
  { path: "/accessibility", name: "AccessibilityPage" },
  { path: "/contact", name: "ContactPage" },
  { path: "/privacy", name: "PrivacyPage" },
  { path: "/tech", name: "TechSupportPage" },
  { path: "/makerspace", name: "MakerspacePage" },
  { path: "/learn", name: "LearnPage" },
  { path: "/learn/catalog", name: "LearnCatalogPage" },
  { path: "/learning-paths", name: "LearningPathsPage" },
  { path: "/learn/labs", name: "LabsPage" },
  { path: "/strategic-plan", name: "StrategicPlanPage" },
] as const

/**
 * Auth page routes (no layout)
 */
export const AUTH_PAGE_ROUTES = [
  { path: "/login", name: "LoginPage" },
  { path: "/register", name: "RegisterPage" },
  { path: "/forgot-password", name: "ForgotPasswordPage" },
  { path: "/reset-password", name: "ResetPasswordPage" },
  { path: "/verify-email", name: "VerifyEmailPage" },
] as const
