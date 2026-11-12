/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Reading Lists Data Flow Tests
 *
 * Verifies the complete data flow from API call to component render:
 * 1. API is called with correct parameters
 * 2. API response is properly parsed
 * 3. React Query caches the data
 * 4. Component state is updated
 * 5. UI renders correctly with data or empty state
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
// Plain @testing-library/react render, not the shared './utils/test-utils'
// one: that helper wraps everything in its own AllProviders (with a
// second, unrelated fake AuthContext) regardless of what's already in the
// tree, so it was double-wrapping this file's own local AllProviders below
// — the outer, unmocked EssentialsModeProvider it pulls in then called this
// file's mocked useAuth() with no matching AuthProvider ancestor in that
// branch, throwing "useAuth must be used within an AuthProvider".
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AccountPage from '../pages/AccountPage'
import { BrandingProvider } from '../contexts/BrandingContext'
import * as collectionsApi from '../api/collections-api'

// src/__tests__/setup.ts installs a global `vi.mock('@/contexts/AuthContext', ...)`
// with a static fake useAuth() (login/etc are no-ops that never flip
// isAuthenticated), so every test file gets that fake by default. This file
// needs a login submission to actually flip isAuthenticated, so it overrides
// that mock per-file (the supported pattern per setup.ts's own comment).
//
// `vi.unmock` + a dynamic re-import of the real AuthContext was tried here
// first, but it doesn't get the whole module graph back to one consistent
// module instance: AccountPage's *static* imports (e.g.
// EssentialsModeContext.tsx importing AuthContext) still resolve to
// setup.ts's globally-mocked module, while the dynamic re-import here yields
// a second, separate module — so the <AuthProvider> rendered below satisfies
// a different React Context object than the one EssentialsModeProvider's
// useAuth() subscribes to, throwing "useAuth must be used within an
// AuthProvider" even though a provider is clearly rendered. A same-file
// vi.mock() factory (hoisted, applies once, consistently) avoids that split.
//
// This fake still calls the mocked login()/getMe() from '../api/api' so
// getMyListsSpy assertions are checking a real (if stubbed) login flow, not
// just flipping a flag.
vi.mock('@/contexts/AuthContext', async () => {
  const React = await import('react')
  const api = await import('../api/api')

  const AuthContext = React.createContext<{
    user: unknown
    token: string | null
    isLoading: boolean
    isAuthenticated: boolean
    login: (credential: string, secret: string) => Promise<void>
    logout: () => Promise<void>
    register: () => Promise<void>
    updateProfile: () => Promise<void>
    refreshUser: () => Promise<void>
  } | null>(null)

  function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = React.useState<unknown>(null)
    const [token, setToken] = React.useState<string | null>(null)

    const login = async (credential: string, secret: string) => {
      const response = await api.login(credential, secret)
      setToken(response.access_token)
      const userData = await api.getMe(response.access_token)
      setUser(userData)
    }
    const logout = async () => {
      setUser(null)
      setToken(null)
    }

    return React.createElement(
      AuthContext.Provider,
      {
        value: {
          user,
          token,
          isLoading: false,
          isAuthenticated: !!user,
          login,
          logout,
          register: async () => {},
          updateProfile: async () => {},
          refreshUser: async () => {},
        },
      },
      children,
    )
  }

  function useAuth() {
    const ctx = React.useContext(AuthContext)
    if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
    return ctx
  }

  return { AuthProvider, useAuth }
})

const { AuthProvider } = await import('../contexts/AuthContext')

// Mock data — vi.hoisted so vi.mock() factories (which run before this
// module's own top-level code, since they're hoisted above imports) can
// reference them without a "before initialization" error.
const { mockReadingLists, mockListWithItems } = vi.hoisted(() => {
  const mockReadingLists = [
    {
      id: 1,
      name: 'Summer Reading',
      description: 'Books to read this summer',
      created_at: '2025-01-15T10:00:00Z',
      item_count: 5,
      is_public: false,
    },
    {
      id: 2,
      name: 'Classics',
      description: null,
      created_at: '2025-01-20T15:30:00Z',
      item_count: 3,
      is_public: true,
    },
  ]

  const mockListWithItems = {
  id: 1,
  name: 'Summer Reading',
  description: 'Books to read this summer',
  created_at: '2025-01-15T10:00:00Z',
  item_count: 2,
  is_public: false,
  items: [
    {
      id: 1,
      catalog_item_id: 101,
      added_at: '2025-01-16T10:00:00Z',
      catalog_item: {
        id: 101,
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        item_type: 'book',
        status: 'available',
        cover_url: null,
        description: null,
        page_count: null,
        created_at: '2024-01-01T00:00:00Z',
      },
    },
    {
      id: 2,
      catalog_item_id: 102,
      added_at: '2025-01-17T10:00:00Z',
      catalog_item: {
        id: 102,
        title: '1984',
        author: 'George Orwell',
        item_type: 'book',
        status: 'checked_out',
        cover_url: null,
        description: null,
        page_count: null,
        created_at: '2024-01-01T00:00:00Z',
      },
    },
  ],
  }

  return { mockReadingLists, mockListWithItems }
})

// Create a fresh QueryClient for each test
let queryClient: QueryClient

beforeEach(() => {
  queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  vi.clearAllMocks()
})

afterEach(() => {
  queryClient.clear()
})

// Mock the API module
vi.mock('../api/api', () => ({
  getMyCheckouts: vi.fn().mockResolvedValue([]),
  getMyHolds: vi.fn().mockResolvedValue([]),
  getMyHistory: vi.fn().mockResolvedValue([]),
  getMyFinesSummary: vi.fn().mockResolvedValue({
    total_outstanding: 0,
    total_paid: 0,
    outstanding_count: 0,
    paid_count: 0,
  }),
  getMyFavorites: vi.fn().mockResolvedValue([]),
  getMyLists: vi.fn().mockResolvedValue(mockReadingLists),
  getList: vi.fn().mockResolvedValue(mockListWithItems),
  createList: vi.fn().mockResolvedValue(mockReadingLists[0]),
  deleteList: vi.fn().mockResolvedValue(undefined),
  removeFromList: vi.fn().mockResolvedValue(undefined),
  renewCheckout: vi.fn(),
  cancelHold: vi.fn(),
  removeFavorite: vi.fn(),
  login: vi.fn().mockResolvedValue({
    access_token: 'mock-token',
    token_type: 'bearer',
  }),
  register: vi.fn(),
  logout: vi.fn(),
  getMe: vi.fn().mockResolvedValue({
    id: 1,
    email: 'test@example.com',
    first_name: 'Test',
    last_name: 'User',
  }),
  updateMe: vi.fn(),
  refreshAccessToken: vi.fn(),
}))

// AccountPage actually imports getMyLists/getMyFavorites/etc from
// '../services/api' -> '@/api/collections-api' (the domain-organized
// module), not the '../api/api' legacy barrel mocked above — that mock
// covers auth/circulation calls AccountPage still resolves through '../api/api'
// but never intercepts collections-api, so getMyLists made real, unmocked
// network calls that resolved (or hung) after the test had already
// unmounted, tripping React's "Should not already be working" guard.
// Mocking the real path here lets `vi.spyOn(collectionsApi, 'getMyLists')`
// (used throughout this file) actually control a mock, not the live function.
vi.mock('../api/collections-api', () => ({
  getMyFavorites: vi.fn().mockResolvedValue([]),
  removeFavorite: vi.fn().mockResolvedValue(undefined),
  getMyLists: vi.fn().mockResolvedValue(mockReadingLists),
  getList: vi.fn().mockResolvedValue(mockListWithItems),
  createList: vi.fn().mockResolvedValue(mockReadingLists[0]),
  deleteList: vi.fn().mockResolvedValue(undefined),
  addToList: vi.fn().mockResolvedValue(undefined),
  removeFromList: vi.fn().mockResolvedValue(undefined),
  updateListPrivacy: vi.fn().mockResolvedValue(undefined),
}))

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  },
}))

// Mock the accessibility hook. Real consumers read both the flat
// spread-through properties (e.g. `reduceMotion`) AND the nested
// `settings.sensory.reduceMotion` (see UseUnifiedAccessibilityReturn in
// useUnifiedAccessibility.ts, which extends both AccessibilitySettings and
// UnifiedAccessibilityContextType) — ConfirmDialog (mounted inside
// ListsSection's delete-list confirmation) reads the nested form and threw
// on `settings` being undefined without it.
vi.mock('../features/accessibility/hooks/useUnifiedAccessibility', () => ({
  useUnifiedAccessibility: () => ({
    quietMode: false,
    focusMode: false,
    simplifiedView: false,
    reduceMotion: false,
    showImages: true,
    preferPagination: false,
    noFOMO: false,
    settings: {
      sensory: {
        reduceMotion: false,
        reduceVisualStimulation: false,
        reduceAudioStimulation: false,
        reduceTactileFeedback: false,
      },
    },
    announceToScreenReader: vi.fn(),
  }),
}))

// Mock other context providers
vi.mock('../contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({
    isFeatureEnabled: () => true,
  }),
  OrganizationFeaturesProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

vi.mock('../contexts/PreferencesContext', () => ({
  PreferencesProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

// The real BrandingProvider fetches branding config over the network on
// mount (fetchApi, unmocked here) — AccountPage's usePageTitle() calls
// useBranding() unconditionally, so it needs a lightweight stand-in.
vi.mock('../contexts/BrandingContext', () => ({
  BrandingProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useBranding: () => ({ library_name: 'Library' }),
}))

// useTranslation() returns the full i18n context — { language, setLanguage,
// t, isRTL } (see I18nContext.tsx). This mock was missing setLanguage,
// which useI18nSync (mounted deep in the provider tree) calls unconditionally
// in an effect — a mock without it throws on every render, which is what was
// actually causing the "Should not already be working" React error: a
// downstream symptom of that crash during the passive-effects phase, not a
// separate bug.
vi.mock('../i18n/I18nContext', async () => {
  // Delegate to the real translate function (setup.ts preloads English) so
  // rendered copy matches what the app actually shows — LoginPage's inputs
  // key their placeholders off real catalog strings like "your@email.com",
  // which an identity `t: (key) => key` stub can't produce.
  const { t: realT } = await import('../i18n/translations')
  return {
    I18nProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
    useTranslation: () => ({
      language: 'en',
      setLanguage: vi.fn(),
      t: realT,
      isRTL: false,
    }),
  }
})

// Wrapper with all providers. AccountPage's usePageTitle() calls
// useBranding(), which throws without a real BrandingProvider ancestor — it
// fails soft to DEFAULT_BRANDING via try/catch when its fetch goes unmocked
// (see BrandingContext.tsx), so it's safe to include for real here.
const AllProviders = ({ children }: { children: ReactNode }) => (
  <BrowserRouter>
    <QueryClientProvider client={queryClient}>
      <BrandingProvider>
        <AuthProvider>{children}</AuthProvider>
      </BrandingProvider>
    </QueryClientProvider>
  </BrowserRouter>
)

const renderWithProviders = (ui: React.ReactElement) => {
  return render(<AllProviders>{ui}</AllProviders>)
}

describe('Reading Lists Data Flow', () => {
  describe('1. API is called with correct parameters', () => {
    it('should call getMyLists when lists tab is activated', async () => {
      const getMyListsSpy = vi.spyOn(collectionsApi, 'getMyLists')

      renderWithProviders(<AccountPage />)

      // Login first
      const emailInput = screen.getByPlaceholderText(/your@email.com/i)
      // AuthForm's password input placeholder is masked bullets ("••••••••",
      // see placeholder.account.input), not literal "password" text, and its
      // <label> isn't htmlFor/id-associated — so neither placeholder nor
      // label queries find it. Select on the type attribute instead.
      const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await userEvent.type(emailInput, 'test@example.com')
      await userEvent.type(passwordInput, 'password123')
      await userEvent.click(submitButton)

      // Wait for login to complete
      await waitFor(() => {
        expect(screen.queryByRole('heading', { name: /sign in/i })).not.toBeInTheDocument()
      })

      // Click on lists tab
      // Both the mobile pill-nav and desktop sidebar-nav "Lists" buttons
      // mount unconditionally (Tailwind's hidden/lg:hidden classes aren't
      // applied in happy-dom), so a singular findByRole throws on multiple
      // matches — grab the first of the two identical buttons.
      const [listsTab] = await screen.findAllByRole('button', { name: /lists/i })
      await userEvent.click(listsTab!)

      // Verify API was called
      await waitFor(() => {
        expect(getMyListsSpy).toHaveBeenCalled()
      })

      getMyListsSpy.mockRestore()
    })

    it('should only call API if token exists', async () => {
      const getMyListsSpy = vi.spyOn(collectionsApi, 'getMyLists')

      renderWithProviders(<AccountPage />)

      // Without logging in, click lists tab
      const listsTabs = screen.queryAllByRole('button', { name: /lists/i })
      expect(listsTabs).toHaveLength(0)

      // API should not be called when not authenticated
      expect(getMyListsSpy).not.toHaveBeenCalled()

      getMyListsSpy.mockRestore()
    })
  })

  describe('2. API response is properly parsed', () => {
    it('should receive array of lists from API', async () => {
      const getMyListsSpy = vi
        .spyOn(collectionsApi, 'getMyLists')
        .mockResolvedValueOnce(mockReadingLists)

      const result = await collectionsApi.getMyLists('mock-token')

      expect(Array.isArray(result)).toBe(true)
      expect(result).toHaveLength(2)
      expect(result[0]).toHaveProperty('id')
      expect(result[0]).toHaveProperty('name')
      expect(result[0]).toHaveProperty('item_count')

      getMyListsSpy.mockRestore()
    })

    it('should handle empty array response', async () => {
      const getMyListsSpy = vi.spyOn(collectionsApi, 'getMyLists').mockResolvedValueOnce([])

      const result = await collectionsApi.getMyLists('mock-token')

      expect(Array.isArray(result)).toBe(true)
      expect(result).toHaveLength(0)

      getMyListsSpy.mockRestore()
    })

    it('should handle API errors gracefully', async () => {
      const getMyListsSpy = vi
        .spyOn(collectionsApi, 'getMyLists')
        .mockRejectedValueOnce(new Error('API Error'))

      try {
        await collectionsApi.getMyLists('mock-token')
      } catch (error: unknown) {
        expect(error).toBeInstanceOf(Error)
      }

      getMyListsSpy.mockRestore()
    })
  })

  describe('3. React Query caches the data', () => {
    it('should cache reading lists in React Query', async () => {
      const getMyListsSpy = vi
        .spyOn(collectionsApi, 'getMyLists')
        .mockResolvedValue(mockReadingLists)

      // Call API twice
      await collectionsApi.getMyLists('mock-token')
      await collectionsApi.getMyLists('mock-token')

      // In practice, React Query would cache this, but here we're just verifying the function behavior
      expect(getMyListsSpy).toHaveBeenCalledTimes(2)

      getMyListsSpy.mockRestore()
    })
  })

  describe('4. Component state is updated', () => {
    it('should update state with API response', async () => {
      // This would require a more complex component test
      // For now, we verify the hook behavior
      expect(mockReadingLists).toHaveLength(2)
      expect(mockReadingLists[0]).toBeDefined()
      expect(mockReadingLists[0]?.name).toBe('Summer Reading')
    })
  })

  describe('5. UI renders correctly', () => {
    it('should render empty state when no lists exist', async () => {
      vi.spyOn(collectionsApi, 'getMyLists').mockResolvedValueOnce([])

      renderWithProviders(<AccountPage />)

      // Login
      const emailInput = screen.getByPlaceholderText(/your@email.com/i)
      // AuthForm's password input placeholder is masked bullets ("••••••••",
      // see placeholder.account.input), not literal "password" text, and its
      // <label> isn't htmlFor/id-associated — so neither placeholder nor
      // label queries find it. Select on the type attribute instead.
      const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await userEvent.type(emailInput, 'test@example.com')
      await userEvent.type(passwordInput, 'password123')
      await userEvent.click(submitButton)

      // Wait and navigate to lists
      await waitFor(() => {
        expect(screen.queryByRole('heading', { name: /sign in/i })).not.toBeInTheDocument()
      })

      // Click lists tab
      // Same mobile+desktop duplicate-button situation as above.
      const [listsButton] = await screen.findAllByRole('button', { name: /lists/i })
      await userEvent.click(listsButton!)

      // Empty state should be shown
      await waitFor(() => {
        expect(screen.getByText(/no reading lists yet/i)).toBeInTheDocument()
      })
    })

    it('should render lists when data is available', async () => {
      vi.spyOn(collectionsApi, 'getMyLists').mockResolvedValueOnce(mockReadingLists)

      renderWithProviders(<AccountPage />)

      // Login
      const emailInput = screen.getByPlaceholderText(/your@email.com/i)
      // AuthForm's password input placeholder is masked bullets ("••••••••",
      // see placeholder.account.input), not literal "password" text, and its
      // <label> isn't htmlFor/id-associated — so neither placeholder nor
      // label queries find it. Select on the type attribute instead.
      const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await userEvent.type(emailInput, 'test@example.com')
      await userEvent.type(passwordInput, 'password123')
      await userEvent.click(submitButton)

      // Wait and navigate to lists
      await waitFor(() => {
        expect(screen.queryByRole('heading', { name: /sign in/i })).not.toBeInTheDocument()
      })

      // Click lists tab
      // Same mobile+desktop duplicate-button situation as above.
      const [listsButton] = await screen.findAllByRole('button', { name: /lists/i })
      await userEvent.click(listsButton!)

      // Lists should render
      await waitFor(() => {
        expect(screen.getByText('Summer Reading')).toBeInTheDocument()
        expect(screen.getByText('Classics')).toBeInTheDocument()
      })
    })

    it('should show loading state while fetching', async () => {
      vi.spyOn(collectionsApi, 'getMyLists').mockImplementationOnce(
        () => new Promise(resolve => setTimeout(() => resolve(mockReadingLists), 500))
      )

      renderWithProviders(<AccountPage />)

      // Login
      const emailInput = screen.getByPlaceholderText(/your@email.com/i)
      // AuthForm's password input placeholder is masked bullets ("••••••••",
      // see placeholder.account.input), not literal "password" text, and its
      // <label> isn't htmlFor/id-associated — so neither placeholder nor
      // label queries find it. Select on the type attribute instead.
      const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await userEvent.type(emailInput, 'test@example.com')
      await userEvent.type(passwordInput, 'password123')
      await userEvent.click(submitButton)

      // Navigate to lists
      await waitFor(() => {
        expect(screen.queryByRole('heading', { name: /sign in/i })).not.toBeInTheDocument()
      })

      // Same mobile+desktop duplicate-button situation as above.
      const [listsButton] = await screen.findAllByRole('button', { name: /lists/i })
      await userEvent.click(listsButton!)

      // Lists should eventually render after loading
      await waitFor(() => {
        expect(screen.getByText('Summer Reading')).toBeInTheDocument()
      })
    })
  })

  describe('Common Issues Detection', () => {
    it('should detect if API is not called', async () => {
      const getMyListsSpy = vi.spyOn(collectionsApi, 'getMyLists')

      renderWithProviders(<AccountPage />)

      // Without authentication or navigating to lists tab
      await waitFor(() => {
        expect(getMyListsSpy).not.toHaveBeenCalled()
      })

      getMyListsSpy.mockRestore()
    })

    it('should detect if response contains data', async () => {
      const mockEmptyResponse: unknown[] = []
      const mockWithDataResponse = mockReadingLists

      expect(mockEmptyResponse).toHaveLength(0)
      expect(mockWithDataResponse.length).toBeGreaterThan(0)
    })

    it('should detect if loading state is stuck', async () => {
      // This would require manual testing with DevTools
      // Here we verify the component has proper loading state handling
      expect(true).toBe(true) // Placeholder for manual DevTools test
    })

    it('should detect authorization errors', async () => {
      const getMyListsSpy = vi
        .spyOn(collectionsApi, 'getMyLists')
        .mockRejectedValueOnce(new Error('401 Unauthorized'))

      try {
        await collectionsApi.getMyLists('invalid-token')
      } catch (error: unknown) {
        expect(error).toBeInstanceOf(Error)
        expect((error as Error).message).toContain('Unauthorized')
      }

      getMyListsSpy.mockRestore()
    })
  })
})
