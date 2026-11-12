/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Smoke test: HomePage renders the rotating-quote blockquote end-to-end when
 * the public homepage-quotes API returns data.
 *
 * Catches the silent-null-render class of regression -- e.g., PR #1051 shipped
 * a rotating-quote section that never appeared in prod because the
 * homepage-quotes api module dereferenced response.data on a bare array (axios
 * envelope assumption), getHomepageQuotes returned undefined, React Query went
 * to "error" state, useHomePageQuote returned null, and the section silently
 * rendered nothing. This test exercises the full hook -> api module -> api
 * wrapper pipeline so the same class of bug fails CI instead of shipping.
 */
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}))

// Mock the api-client wrapper to return the parsed body DIRECTLY (matches the
// real api-client.ts contract, where api.get returns res.json()). Leaving
// useHomepageQuotes / useHomePageQuote / getHomepageQuotes UNMOCKED is
// deliberate -- they run end-to-end against this wrapper so any future
// response.data envelope-unwrap regression trips the assertion below.
vi.mock('@/lib/api-client', () => ({
  api: apiMock,
  fetchApi: vi.fn().mockResolvedValue(undefined),
  isApiError: () => false,
}))

// Contexts: safe defaults. HomePage redirects to /welcome if !setupComplete,
// so setupComplete MUST be true or nothing renders.
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: null }),
}))
vi.mock('@/contexts/OnboardingContext', () => ({
  useOnboarding: () => ({ shouldShowPatronOnboarding: false }),
}))
vi.mock('@/contexts/EssentialsModeContext', () => ({
  useEssentialsMode: () => ({ isEssentialsMode: false }),
}))
vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({ isFeatureEnabled: () => true }),
}))
vi.mock('@/contexts/BrandingContext', () => ({
  useBrandingContext: () => ({ setupComplete: true }),
  // PlanYourVisit (lazy-loaded inside HomePage, see mechanism note below)
  // calls the separate useBranding() hook, not useBrandingContext().
  useBranding: () => ({ quiet_hours: null, sensory_friendly_times: null, low_stim_seating: null }),
}))
vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (_k: string, fallback?: string) => fallback ?? _k,
    language: 'en',
  }),
}))
vi.mock('@/hooks/usePageTitle', () => ({ usePageTitle: vi.fn() }))

// Accessibility: not calm, not reduce-motion (so the rotating-quote path runs)
vi.mock('@/features/accessibility', () => ({
  useUnifiedAccessibility: () => ({
    settings: { reduceMotion: false },
    getCurrentPreset: () => undefined,
  }),
}))

// Stub heavy non-lazy children -- we only assert on the quote block here.
vi.mock('../../components/HeroSection', () => ({
  default: () => <div data-testid="hero-section">hero</div>,
}))
vi.mock('@/components/LibraryPulse', () => ({
  default: () => <div data-testid="library-pulse" />,
}))
vi.mock('@/components/home/TodayStrip', () => ({
  default: () => <div data-testid="today-strip" />,
}))
vi.mock('@/components/SectionDivider', () => ({
  default: () => <hr data-testid="section-divider" />,
}))
vi.mock('@/components/Skeleton', () => ({
  default: () => <div data-testid="skeleton" />,
}))

// Stub lazy children so Suspense resolves immediately.
vi.mock('@/components/EssentialsHomePage', () => ({ default: () => <div /> }))
vi.mock('@/components/ActionGrid', () => ({ default: () => <div data-testid="action-grid" /> }))
vi.mock('@/components/ComputerLabStatus', () => ({ default: () => <div data-testid="computer-lab" /> }))
vi.mock('@/components/BlogCard', () => ({ default: () => <div data-testid="blog-card" /> }))
vi.mock('@/components/home/HeroPick', () => ({ default: () => <div data-testid="hero-pick" /> }))
vi.mock('@/components/home/TopicalShelf', () => ({ default: () => <div data-testid="topical-shelf" /> }))
vi.mock('@/components/UpcomingProgramsStrip', () => ({ default: () => <div data-testid="programs-strip" /> }))

// API modules HomePage useQuery's against -- mock to safe-empty so the
// queries resolve without throwing. (These do not exercise the api-client
// wrapper bug; only the quotes path does.)
vi.mock('@/api/api', () => ({
  getEvents: vi.fn().mockResolvedValue({ items: [] }),
}))
vi.mock('@/services/blog-api', () => ({
  getBlogPosts: vi.fn().mockResolvedValue({ items: [] }),
}))
vi.mock('@/api/announcements-api', () => ({
  getAnnouncements: vi.fn().mockResolvedValue({ items: [] }),
}))
vi.mock('@/api/domains/content/homepage-content-api', () => ({
  getIsOpen: vi.fn().mockResolvedValue({ is_open: true }),
  getLibraryHours: vi.fn().mockResolvedValue([]),
}))
vi.mock('@/api/branch-api', () => ({
  listBranches: vi.fn().mockResolvedValue([]),
}))
vi.mock('@/api/domains/catalog/linked-data-api', () => ({
  getLibrarySchemaOrg: vi.fn().mockResolvedValue(null),
}))
vi.mock('@/api/home', () => ({
  getHomePage: vi.fn().mockResolvedValue({ shelves: [] }),
}))

import HomePage from '../HomePage'

const QUOTE = {
  id: 1,
  quote_text: 'Smoke-test quote text -- distinctive enough to grep',
  attribution: 'Smoke Author',
}

function renderHomePage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('HomePage smoke test (render-presence)', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.get.mockImplementation(async (url: string) => {
      if (url.startsWith('/homepage-quotes')) return [QUOTE]
      return []
    })
  })

  it('renders the rotating-quote blockquote when the quotes API returns data', async () => {
    renderHomePage()
    await waitFor(() => {
      expect(screen.getByText(QUOTE.quote_text, { exact: false })).toBeInTheDocument()
    })
    const quoteEl = screen.getByText(QUOTE.quote_text, { exact: false })
    expect(quoteEl.closest('blockquote')).toBeInTheDocument()
    expect(screen.getByText(QUOTE.attribution, { exact: false })).toBeInTheDocument()
  })

  it('renders the hero section', () => {
    renderHomePage()
    expect(screen.getByTestId('hero-section')).toBeInTheDocument()
  })
})
