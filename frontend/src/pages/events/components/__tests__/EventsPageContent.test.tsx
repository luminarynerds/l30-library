/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * EventsPageContent Tests
 *
 * Covers accessibility + i18n fixes shipped with the events-page a11y PR:
 *   - aria-live="polite" (not "assertive") on the results status region
 *   - 300ms debounce of the free-text search before refetching events
 *   - i18n-keyed labels for the "Clear filters" empty-state button
 *
 * NOTE: We intentionally avoid src/__tests__/utils/test-utils because that
 * module registers a hoisted `vi.mock` of `../../api/api` that omits the
 * events exports (getEventTags etc.). Mirrors the pattern used by
 * src/__tests__/pages/EventsPage.test.tsx.
 */

import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from 'vitest'
import type { ReactNode } from 'react'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// ---- Mocks (must be at module level, before component imports) ------------

const getEventsMock = vi.fn()
const getEventTagsMock = vi.fn().mockResolvedValue([])
const cancelRegistrationMock = vi.fn().mockResolvedValue({})

vi.mock('@/api/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: null }),
    post: vi.fn().mockResolvedValue({ data: null }),
    put: vi.fn().mockResolvedValue({ data: null }),
    delete: vi.fn().mockResolvedValue({ data: null }),
  },
  getEvents: (...args: unknown[]) => getEventsMock(...args),
  getEventTags: (...args: unknown[]) => getEventTagsMock(...args),
  cancelRegistration: (...args: unknown[]) => cancelRegistrationMock(...args),
  getMe: vi.fn().mockResolvedValue(null),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  refreshAccessToken: vi.fn(),
}))

vi.mock('@/api/events-api', () => ({
  getEventCategories: vi.fn().mockResolvedValue([]),
  getEventAudiences: vi.fn().mockResolvedValue([]),
}))

vi.mock('@/api/organization-features-api', () => ({
  getOrganizationFeatures: vi.fn().mockResolvedValue({}),
}))

vi.mock('@/hooks/useEventPersonalization', () => ({
  useEventPersonalization: () => ({
    registrations: [],
    bookmarks: [],
    bookmarksCount: 0,
    preferences: { categories: [], audiences: [] },
    userEmail: null,
    isRegistered: () => false,
    isBookmarked: () => false,
    matchesPreferences: () => false,
    addRegistration: vi.fn(),
    removeRegistration: vi.fn(),
    toggleBookmark: vi.fn(),
    removeBookmark: vi.fn(),
    setPreferences: vi.fn(),
    toggleCategory: vi.fn(),
    toggleAudience: vi.fn(),
  }),
}))

vi.mock('@/features/accessibility/hooks/useAccessibility', () => ({
  useAccessibility: () => ({
    settings: { reduceMotion: false, highContrast: false, largerText: false },
    updateSetting: vi.fn(),
  }),
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

import EventsPageContent from '../EventsPageContent'
import { I18nProvider } from '@/i18n/I18nContext'
import { BrandingProvider } from '@/contexts/BrandingContext'

// ---- Helpers --------------------------------------------------------------

// Captures the current MemoryRouter location.search across renders so
// URL write-back tests can assert on it after a filter change.
let lastLocationSearch = ''
function LocationProbe() {
  const loc = useLocation()
  lastLocationSearch = loc.search
  return null
}

function buildWrapper(queryClient: QueryClient, initialEntries: string[] = ['/events']) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter
        initialEntries={initialEntries}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <QueryClientProvider client={queryClient}>
          <BrandingProvider>
            <I18nProvider>
              {children}
              <LocationProbe />
            </I18nProvider>
          </BrandingProvider>
        </QueryClientProvider>
      </MemoryRouter>
    )
  }
}

function renderPage(initialEntries?: string[]) {
  lastLocationSearch = initialEntries?.[0]?.includes('?')
    ? `?${initialEntries[0].split('?')[1]}`
    : ''
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0, gcTime: 0 } },
  })
  return render(<EventsPageContent />, { wrapper: buildWrapper(queryClient, initialEntries) })
}

function emptyEventsPayload() {
  return { data: [], total: 0, page: 1, per_page: 20 }
}

function singleEventPayload() {
  return {
    data: [
      {
        id: 42,
        title: 'Storytime',
        description: 'Stories for kids',
        start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
        end_time: new Date(Date.now() + 25 * 60 * 60 * 1000).toISOString(),
        location: 'Children Room',
        category: 'storytime',
        audience: 'children',
        registration_required: false,
        spots_remaining: null,
        max_attendees: null,
        is_featured: false,
        tags: [],
        created_at: new Date().toISOString(),
      },
    ],
    total: 1,
    page: 1,
    per_page: 20,
  }
}

// ---- Tests ----------------------------------------------------------------

describe('EventsPageContent — a11y + i18n fixes', () => {
  beforeAll(async () => {
    // Preload English translations -- normally awaited by main.tsx before mounting.
  })

  beforeEach(() => {
    vi.clearAllMocks()
    getEventsMock.mockResolvedValue(emptyEventsPayload())
    getEventTagsMock.mockResolvedValue([])
  })

  it('results status region uses aria-live polite, not assertive', async () => {
    renderPage()

    const statusRegion = await screen.findByRole('status')
    expect(statusRegion).toHaveAttribute('aria-live', 'polite')
    expect(statusRegion).not.toHaveAttribute('aria-live', 'assertive')
    expect(statusRegion).toHaveAttribute('aria-atomic', 'true')
  })

  it('clear filters empty-state button uses the translated label', async () => {
    renderPage()

    const search = await screen.findByPlaceholderText(/search events/i)
    await userEvent.type(search, 'banana-no-match')

    const clearButton = await screen.findByRole('button', { name: /clear filters/i })
    expect(clearButton).toHaveTextContent(/clear filters/i)
    expect(clearButton).toHaveAttribute('aria-label', 'Clear filters')
  })

  it('debounces the search input — no refetch within 300ms of typing', async () => {
    const { fireEvent } = await import('@testing-library/react')
    renderPage()

    // Wait for the initial empty-state fetch to land before installing fake timers.
    const search = await screen.findByPlaceholderText(/search events/i)
    const initialCalls = getEventsMock.mock.calls.length
    expect(initialCalls).toBeGreaterThanOrEqual(1)

    vi.useFakeTimers()
    try {
      // Simulate the entire phrase landing in one render commit (which is what
      // a fast typist or paste effectively looks like to React); the debounce
      // hook still must withhold the new search for ~300ms.
      await act(async () => {
        fireEvent.change(search, { target: { value: 'banana' } })
      })

      // Within the debounce window no NEW fetch should carry search.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(299)
      })
      const searchedBefore = getEventsMock.mock.calls.some(
        ([args]) =>
          args && typeof args === 'object' && 'search' in args && (args as { search?: string }).search,
      )
      expect(searchedBefore).toBe(false)

      // After the debounce elapses, the next fetch should include search=banana.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(50)
      })
      const searchedAfter = getEventsMock.mock.calls.some(
        ([args]) =>
          args && typeof args === 'object' && 'search' in args && (args as { search?: string }).search === 'banana',
      )
      expect(searchedAfter).toBe(true)
    } finally {
      vi.useRealTimers()
    }
  })
})

// ---- PR #5 — landing reorder, mobile filter collapse, URL persistence ------

describe('EventsPageContent — landing reorder', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getEventsMock.mockResolvedValue(singleEventPayload())
    getEventTagsMock.mockResolvedValue([])
  })

  it('renders chips-nav AFTER the Today & this week band and BEFORE the filters heading', async () => {
    renderPage()

    // The merged "Today & this week" band (HappeningNow + day strip) renders
    // above the quick chips.
    const happening = await screen.findByRole('region', { name: /today & this week/i })
    const chipsNav = await screen.findByRole('navigation', { name: /event quick filters/i })
    const filtersHeading = await screen.findByRole('heading', { name: /filters/i })

    // Node.DOCUMENT_POSITION_FOLLOWING === 4 means "argument is after this node".

    expect(happening.compareDocumentPosition(chipsNav) & 4).toBe(4)

    expect(chipsNav.compareDocumentPosition(filtersHeading) & 4).toBe(4)
  })
})

describe('EventsPageContent — mobile filter collapse', () => {
  const realMatchMedia = window.matchMedia
  beforeEach(() => {
    vi.clearAllMocks()
    getEventsMock.mockResolvedValue(emptyEventsPayload())
    getEventTagsMock.mockResolvedValue([])
  })
  afterEach(() => {
    window.matchMedia = realMatchMedia
  })

  function mockMatchMedia(isMobile: boolean) {
    window.matchMedia = vi.fn().mockImplementation((q: string) => ({
      matches: q.includes('max-width: 767px') ? isMobile : !isMobile,
      media: q,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
    })) as unknown as typeof window.matchMedia
  }

  it('collapses the filter body on mobile when no URL filter is active', async () => {
    mockMatchMedia(true)
    renderPage(['/events'])
    const toggle = await screen.findByRole('button', { name: /filters/i })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
  })

  it('keeps the filter body expanded on mobile when a filter is active in the URL', async () => {
    mockMatchMedia(true)
    renderPage(['/events?category=storytime'])
    const toggle = await screen.findByRole('button', { name: /filters/i })
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
  })

  it('keeps the filter body expanded on desktop even with no active filters', async () => {
    mockMatchMedia(false)
    renderPage(['/events'])
    const toggle = await screen.findByRole('button', { name: /filters/i })
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
  })
})

describe('EventsPageContent — URL filter persistence', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getEventsMock.mockResolvedValue(emptyEventsPayload())
    getEventTagsMock.mockResolvedValue([])
  })

  it('hydrates category and tag from URL on mount and includes them in the query', async () => {
    renderPage(['/events?category=storytime&tag=stem'])

    // Wait until the events query was called with hydrated filter values.
    // (initial call may be empty; the post-hydrate call carries category/tag.)
    await screen.findByRole('status')
    const hadHydrated = await vi.waitFor(() => {
      const found = getEventsMock.mock.calls.some(([args]) => {
        if (!args || typeof args !== 'object') return false
        const a = args as { category?: string; tag?: string }
        return a.category === 'storytime' && a.tag === 'stem'
      })
      expect(found).toBe(true)
      return true
    })
    expect(hadHydrated).toBe(true)
  })

  it('hydrates ?past=1 from URL on mount (shows past events)', async () => {
    renderPage(['/events?past=1'])
    await screen.findByRole('status')
    await vi.waitFor(() => {
      const found = getEventsMock.mock.calls.some(([args]) => {
        if (!args || typeof args !== 'object') return false
        return (args as { upcoming?: boolean }).upcoming === false
      })
      expect(found).toBe(true)
    })
  })
})

describe('EventsPageContent — URL filter write-back', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getEventsMock.mockResolvedValue(emptyEventsPayload())
    getEventTagsMock.mockResolvedValue([])
  })

  it('writes ?search= to the URL when the user types in the search box', async () => {
    const user = userEvent.setup()
    renderPage(['/events'])

    const search = await screen.findByPlaceholderText(/search events/i)
    await user.type(search, 'storytime')

    await vi.waitFor(() => {
      expect(lastLocationSearch).toContain('search=storytime')
    })
  })

  it('removes ?search= from the URL when the search input is cleared', async () => {
    const user = userEvent.setup()
    renderPage(['/events?search=storytime'])

    const search = (await screen.findByPlaceholderText(/search events/i)) as HTMLInputElement
    await vi.waitFor(() => expect(search.value).toBe('storytime'))

    await user.clear(search)

    await vi.waitFor(() => {
      expect(lastLocationSearch).not.toContain('search=')
    })
  })
})

describe('EventsPageContent — linear view (events review enhancement #5)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getEventsMock.mockResolvedValue(singleEventPayload())
    getEventTagsMock.mockResolvedValue([])
  })

  it('suppresses the promotional rails but still lists events as flat cards', async () => {
    const user = userEvent.setup()
    renderPage()

    // Default list view: the merged "Today & this week" band is present.
    expect(await screen.findByRole('region', { name: /today & this week/i })).toBeInTheDocument()

    // Switch to Linear view.
    await user.click(screen.getByRole('button', { name: /linear view/i }))

    // The band is gone...
    await vi.waitFor(() => {
      expect(screen.queryByRole('region', { name: /today & this week/i })).toBeNull()
    })
    // ...and the event still renders as a flat EventCard (title Link).
    expect(screen.getByRole('link', { name: 'Storytime' })).toBeInTheDocument()
  })
})

describe('EventsPageContent — dead modal-open path removed', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getEventsMock.mockResolvedValue(singleEventPayload())
    getEventTagsMock.mockResolvedValue([])
  })

  it('clicking a standalone EventCard does NOT open the EventDetailModal', async () => {
    // With one event in the payload, the standalone EventCard renders.
    // PR #5 dropped the outer-container onClick that called setDetailEvent;
    // PR #991 already moved navigation onto the inner title <Link>.
    // We assert the legacy behavior is gone: clicking the card's outer
    // container must NOT cause the EventDetailModal (role="dialog") to mount.
    const user = userEvent.setup()
    const { container } = renderPage(['/events'])

    // Wait for the list to render. The same "Storytime" text shows up in
    // HappeningNowSection AND the standalone EventCard list; we target the
    // standalone card by walking from the canonical detail Link.
    const detailLink = await vi.waitFor(() => {
      const link = container.querySelector('a[href="/events/detail/42"]')
      if (!link) throw new Error('detail link not yet rendered')
      return link as HTMLAnchorElement
    })

    // The card container is one of the link's ancestors. Click the nearest
    // ancestor div (the outer card wrapper) — this is the element that USED
    // to fire `onClick={() => setDetailEvent(event)}` before PR #5.
    const cardWrapper = detailLink.parentElement?.parentElement?.parentElement
    expect(cardWrapper).toBeTruthy()
    if (cardWrapper) {
      await user.click(cardWrapper)
    }

    await act(async () => { await new Promise((r) => setTimeout(r, 10)) })
    expect(screen.queryByRole('dialog')).toBeNull()
  })
})
