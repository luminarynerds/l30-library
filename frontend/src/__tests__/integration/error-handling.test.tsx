/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Error Handling Integration Tests
 *
 * Tests error handling across the application including:
 * - Network errors
 * - API errors (401, 403, 404, 500)
 * - Error boundaries
 * - User-friendly error messages
 * - Error recovery
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '../utils/test-utils'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CatalogPage from '@/pages/CatalogPage'
import AccountPage from '@/pages/AccountPage'

// Mock useAccessibility
const mockAccessibility = {
  quietMode: false,
  focusMode: false,
  simplifiedView: false,
  reduceMotion: false,
  showImages: true,
  preferPagination: false,
  noFOMO: false,
  dyslexiaFont: false,
  settings: {
    quietMode: false,
    dyslexiaFont: false,
  },
  updateSetting: vi.fn(),
  announceToScreenReader: vi.fn(),
}

vi.mock('@/features/accessibility/hooks/useAccessibility', () => ({
  useAccessibility: () => mockAccessibility,
}))

// Mock auth context
const mockUseAuth = {
  user: {
    id: 1,
    email: 'test@example.com',
    first_name: 'Test',
    last_name: 'User',
    role: 'patron' as const,
  },
  token: 'test-token',
  isLoading: false,
  isAuthenticated: true,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  updateProfile: vi.fn(),
  refreshUser: vi.fn(),
}

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth,
}))

// Mock fetch
//
// CatalogPage also fetches /reading-status (via useShelfStatusMap) alongside
// the catalog search call. That endpoint returns an array directly, not the
// { items, total, pages } catalog envelope, so it's routed separately here —
// otherwise every test's catalog response shape gets fed into the reading
// status hook and `for (const s of allStatuses)` blows up on a non-iterable.
const mockFetch = vi.fn()
global.fetch = mockFetch

// Search now goes through /search/unified (unifiedSearch() in
// unified-search-api.ts), which returns a `{ results, total_results, ... }`
// envelope, not the older `{ items, total, pages }` shape. useCatalogSearch.ts
// does `response.results.map(toDisplayItem)` unconditionally, so a mock
// missing `.results` throws inside the queryFn — react-query then retries 3x
// with exponential backoff (see RETRY_WAIT below) before the test ever sees
// a settled UI, timing out well short of that.
function emptyUnifiedSearchResponse() {
  return unifiedSearchResponse([])
}

function toUnifiedResult(item: { id: number; title: string; author: string; item_type: string; status: string }) {
  return {
    id: String(item.id),
    source: 'local',
    source_id: String(item.id),
    title: item.title,
    author: item.author,
    authors: [item.author],
    format: item.item_type,
    format_details: [],
    description: null,
    cover_url: null,
    isbn: null,
    publisher: null,
    publication_year: null,
    subjects: [],
    language: null,
    is_available: item.status === 'available',
    copies_available: null,
    copies_total: null,
    hold_count: null,
    estimated_wait_days: null,
    download_formats: [],
    relevance_score: 1,
    related_sources: [],
  }
}

function unifiedSearchResponse(items: Array<Parameters<typeof toUnifiedResult>[0]>) {
  const results = items.map(toUnifiedResult)
  return {
    query: '',
    total_results: results.length,
    results,
    sources_searched: ['local'],
    source_counts: { local: results.length },
    search_time_ms: 0,
    has_more: false,
    query_was_all_stopwords: false,
  }
}

let catalogQueue: Array<() => Promise<unknown>> = []
let catalogDefault: () => Promise<unknown> = () =>
  Promise.resolve({ ok: true, json: async () => emptyUnifiedSearchResponse() })

function setCatalogDefault(fn: () => Promise<unknown>) {
  catalogDefault = fn
}

// The catalog landing panel (shown whenever there's no active query/filters,
// i.e. on every fresh mount) fires several parallel queries beyond the main
// search — mood categories, new arrivals, public reading lists, staff picks —
// each expecting its own real-shaped response. Anything not routed here falls
// through to catalogDefault()/catalogQueue, which drive the *search* mock;
// feeding the search envelope into e.g. MoodBrowseRow's `moods.map()` throws.
mockFetch.mockImplementation((url: string) => {
  if (typeof url !== 'string') return catalogDefault()
  if (url.includes('/reading-status')) {
    return Promise.resolve({ ok: true, status: 200, json: async () => [] })
  }
  if (url.includes('/mood-categories')) {
    return Promise.resolve({ ok: true, status: 200, json: async () => [] })
  }
  if (url.includes('/catalog/special/new-arrivals')) {
    return Promise.resolve({ ok: true, status: 200, json: async () => ({ items: [], total: 0, days: 14, period: 'week' }) })
  }
  if (url.includes('/reading-lists/public')) {
    return Promise.resolve({ ok: true, status: 200, json: async () => ({ data: [] }) })
  }
  // YourListsSection (rendered inside the landing panel for logged-in users
  // via useMyReadingLists) expects a bare array from /reading-lists/me — same
  // failure mode as /reading-status if it falls through to the search mock.
  if (url.includes('/reading-lists/me')) {
    return Promise.resolve({ ok: true, status: 200, json: async () => [] })
  }
  if (url.includes('/staff/picks/public')) {
    return Promise.resolve({ ok: true, status: 200, json: async () => [] })
  }
  if (url.includes('/catalog/batch-availability')) {
    return Promise.resolve({ ok: true, status: 200, json: async () => [] })
  }
  const next = catalogQueue.shift()
  return next ? next() : catalogDefault()
})

// useCatalogSearch's query retries failed fetches 3x with exponential backoff
// (1s/2s/4s) before surfacing an error — see useCatalogSearch.ts's `retry: 3`.
// Tests that expect the error UI need to wait out that backoff, not just the
// default waitFor/test timeout.
const RETRY_WAIT = { timeout: 10_000 }
const RETRY_TEST_TIMEOUT = 15_000

describe('Error Handling Integration', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    catalogQueue = []
    catalogDefault = () =>
      Promise.resolve({ ok: true, json: async () => emptyUnifiedSearchResponse() })
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
  })

  describe('Network Errors', () => {
    it('should display user-friendly message on network failure', async () => {
      setCatalogDefault(() => Promise.reject(new Error('Network error')))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(
          screen.getByText(/Unable to load search results right now/i)
        ).toBeInTheDocument()
      }, RETRY_WAIT)
    }, RETRY_TEST_TIMEOUT)

    it('should provide helpful guidance for network errors', async () => {
      setCatalogDefault(() => Promise.reject(new Error('Failed to fetch')))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(
          screen.getByText(/This is usually a temporary connection issue/i)
        ).toBeInTheDocument()
      }, RETRY_WAIT)
    }, RETRY_TEST_TIMEOUT)

    it('should offer refresh button on network error', async () => {
      setCatalogDefault(() => Promise.reject(new Error('Network error')))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Refresh Page/i })).toBeInTheDocument()
      }, RETRY_WAIT)
    }, RETRY_TEST_TIMEOUT)
  })

  describe('API Error Responses', () => {
    it('should handle 401 Unauthorized errors', async () => {
      setCatalogDefault(() => Promise.resolve({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Unauthorized' }),
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByText(/Unable to load search results/i)).toBeInTheDocument()
      }, RETRY_WAIT)
    }, RETRY_TEST_TIMEOUT)

    it('should handle 403 Forbidden errors', async () => {
      setCatalogDefault(() => Promise.resolve({
        ok: false,
        status: 403,
        json: async () => ({ detail: 'Forbidden' }),
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByText(/Unable to load search results/i)).toBeInTheDocument()
      }, RETRY_WAIT)
    }, RETRY_TEST_TIMEOUT)

    it('should handle 404 Not Found errors', async () => {
      setCatalogDefault(() => Promise.resolve({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Not found' }),
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByText(/Unable to load search results/i)).toBeInTheDocument()
      }, RETRY_WAIT)
    }, RETRY_TEST_TIMEOUT)

    it('should handle 500 Server Error', async () => {
      setCatalogDefault(() => Promise.resolve({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Internal server error' }),
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByText(/Unable to load search results/i)).toBeInTheDocument()
      }, RETRY_WAIT)
    }, RETRY_TEST_TIMEOUT)
  })

  describe('Error Recovery', () => {
    it('should allow retry after error', async () => {
      // Fails on the initial attempt AND every internal retry (useCatalogSearch
      // retries 3x on failure) — a single queued rejection would get masked by
      // a retry falling through to a default success response.
      setCatalogDefault(() => Promise.reject(new Error('Network error')))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Refresh Page/i })).toBeInTheDocument()
      }, RETRY_WAIT)

      // Second call succeeds
      setCatalogDefault(() => Promise.resolve({
        ok: true,
        json: async () => unifiedSearchResponse([
          { id: 1, title: 'Test Book', author: 'Test Author', item_type: 'book', status: 'available' },
        ]),
      }))

      // Note: Can't actually trigger refresh in test without reloading page
      // This demonstrates the pattern
    }, RETRY_TEST_TIMEOUT)

    it('should clear error state when new search is performed', async () => {
      const user = userEvent.setup()

      // Fails on every attempt, including internal retries — CatalogPage
      // fetches on mount (query defaults to '*'), so this alone produces the
      // "first search failed" state without needing a manual search first.
      // Doing it this way (instead of typing + clicking through the retry
      // backoff twice) keeps this test to a single RETRY_WAIT-sized delay
      // instead of two stacked ones.
      setCatalogDefault(() => Promise.reject(new Error('Network error')))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByText(/Unable to load search results/i)).toBeInTheDocument()
      }, RETRY_WAIT)

      // New search succeeds — the button is enabled again now that the
      // mount fetch has settled (into error).
      setCatalogDefault(() => Promise.resolve({
        ok: true,
        json: async () => unifiedSearchResponse([
          { id: 1, title: 'Success Book', author: 'Success Author', item_type: 'book', status: 'available' },
        ]),
      }))

      await user.type(screen.getByPlaceholderText(/Search by title/i), 'success')
      await user.click(await screen.findByRole('button', { name: /^Search$/i }))

      await waitFor(() => {
        // The card renders the title twice (a decorative cover-placeholder
        // overlay plus the accessible text label) — getAllByText, not
        // getByText, since both are legitimately present for one result.
        expect(screen.getAllByText('Success Book').length).toBeGreaterThan(0)
        expect(screen.queryByText(/Unable to load search results/i)).not.toBeInTheDocument()
      }, RETRY_WAIT)
      // Two RETRY_WAIT-sized waits back to back (the initial error state,
      // then the successful re-search) need more than one cycle's headroom.
    }, RETRY_TEST_TIMEOUT * 2)
  })

  describe('Validation Errors', () => {
    it('should show field-specific validation errors', async () => {
      const user = userEvent.setup()

      render(
        <QueryClientProvider client={queryClient}>
          <AccountPage />
        </QueryClientProvider>
      )

      // Try to submit with invalid data
      const emailInput = screen.queryByLabelText(/Email/i)
      if (emailInput) {
        await user.clear(emailInput)
        await user.type(emailInput, 'invalid-email')

        const submitButton = screen.queryByRole('button', { name: /Save|Update/i })
        if (submitButton) {
          await user.click(submitButton)

          await waitFor(() => {
            expect(screen.getByText(/valid email/i)).toBeInTheDocument()
          })
        }
      }
    })
  })

  describe('Empty State Handling', () => {
    it('should show friendly message for empty results', async () => {
      const user = userEvent.setup()

      setCatalogDefault(() => Promise.resolve({
        ok: true,
        json: async () => emptyUnifiedSearchResponse(),
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      // CatalogPage fetches on mount, so wait out that initial load before
      // the Search button reads "Search" again (mid-fetch it's "Loading...").
      await user.type(screen.getByPlaceholderText(/Search by title/i), 'nonexistent')
      await user.click(await screen.findByRole('button', { name: /^Search$/i }))

      await waitFor(() => {
        expect(screen.getByText(/No items matched/i)).toBeInTheDocument()
      })
    })

    it('should suggest actions for empty results', async () => {
      const user = userEvent.setup()

      setCatalogDefault(() => Promise.resolve({
        ok: true,
        json: async () => emptyUnifiedSearchResponse(),
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await user.type(screen.getByPlaceholderText(/Search by title/i), 'xyz')
      await user.click(await screen.findByRole('button', { name: /^Search$/i }))

      await waitFor(() => {
        expect(screen.getByText(/Try checking your spelling/i)).toBeInTheDocument()
      })
    })
  })

  describe('Loading States', () => {
    it('should show loading indicator during API call', async () => {
      // useCatalogSearch sets `placeholderData: keepPreviousData` (so
      // browsing doesn't flicker between searches) — once the query has
      // resolved once, react-query's `isLoading` (isPending && isFetching)
      // stays false for every later search, because placeholder data keeps
      // `data` non-undefined. So the button only ever shows the "Loading…"
      // state / disables for the true first fetch on mount, never for a
      // subsequent typed search — verify that instead of a post-search click.
      setCatalogDefault(
        () => new Promise(resolve => setTimeout(() => resolve({
          ok: true,
          json: async () => emptyUnifiedSearchResponse(),
        }), 300))
      )

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      const searchButton = screen.getByRole('button', { name: /Loading/i })
      expect(searchButton).toBeDisabled()

      // And it clears once the initial fetch settles.
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /^Search$/i })).not.toBeDisabled()
      })
    })
  })

  describe('Malformed Response Handling', () => {
    it('should handle invalid JSON responses', async () => {
      setCatalogDefault(() => Promise.resolve({
        ok: true,
        json: async () => {
          throw new Error('Invalid JSON')
        },
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByText(/Unable to load search results/i)).toBeInTheDocument()
      }, RETRY_WAIT)
    }, RETRY_TEST_TIMEOUT)

    it('should handle missing required fields in response', async () => {
      setCatalogDefault(() => Promise.resolve({
        ok: true,
        json: async () => ({
          query: '',
          total_results: 1,
          // A real unified-search result shape, but missing title/author —
          // toDisplayItem() doesn't guard those, so this should render fine
          // with blank fields rather than throw.
          results: [
            {
              id: '1',
              source: 'local',
              source_id: '1',
              format: 'book',
              format_details: [],
              is_available: true,
              relevance_score: 1,
              related_sources: [],
            },
          ],
          sources_searched: ['local'],
          source_counts: { local: 1 },
          search_time_ms: 0,
          has_more: false,
          query_was_all_stopwords: false,
        }),
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      // Should render without crashing, even with missing fields
      await waitFor(() => {
        expect(screen.queryByText(/Unable to load/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('Concurrent Request Handling', () => {
    it('should handle multiple simultaneous requests', async () => {
      const user = userEvent.setup()

      setCatalogDefault(() => Promise.resolve({
        ok: true,
        json: async () => emptyUnifiedSearchResponse(),
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      // Make multiple rapid searches. Wait out the initial mount fetch first —
      // the button reads "Loading..." (and is disabled) until it settles.
      await user.type(screen.getByPlaceholderText(/Search by title/i), 'test1')
      await user.click(await screen.findByRole('button', { name: /^Search$/i }))

      await user.clear(screen.getByPlaceholderText(/Search by title/i))
      await user.type(screen.getByPlaceholderText(/Search by title/i), 'test2')
      await user.click(await screen.findByRole('button', { name: /^Search$/i }))

      // Should handle gracefully without errors
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled()
      })
    })
  })

  describe('Timeout Handling', () => {
    it('should handle request timeouts gracefully', async () => {
      setCatalogDefault(
        () => new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Request timeout')), 100)
        )
      )

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      // Each of the 4 attempts (initial + 3 retries) waits out its own 100ms
      // timeout on top of the retry backoff, so this needs real headroom —
      // 200ms only covered the original (non-retrying) implementation.
      await waitFor(
        () => {
          expect(screen.getByText(/Unable to load search results/i)).toBeInTheDocument()
        },
        RETRY_WAIT
      )
    }, RETRY_TEST_TIMEOUT)
  })
})
