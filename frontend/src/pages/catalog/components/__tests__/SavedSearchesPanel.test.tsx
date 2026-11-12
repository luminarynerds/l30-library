/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Covers the patron-facing saved-searches surface: the side panel and the
 * "Save this search" dialog. We mock apiClient at the boundary so the tests
 * exercise the real TanStack Query plumbing in useSavedSearches.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SavedSearchesPanel from '../SavedSearchesPanel'
import SaveThisSearchButton from '../SaveThisSearchButton'

// ---- Hoisted mocks ------------------------------------------------------

const mocks = vi.hoisted(() => ({
  apiClient: vi.fn(),
}))

vi.mock('@/lib/api-client', () => ({
  apiClient: mocks.apiClient,
  ApiError: class ApiError extends Error {
    status: number
    detail: string
    constructor(msg: string, status: number, detail: string) {
      super(msg)
      this.status = status
      this.detail = detail
    }
  },
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { id: 1, email: 'patron@example.org' },
    token: 'test-token',
  }),
}))

vi.mock('@/features/accessibility/hooks/useUnifiedAccessibility', () => ({
  useUnifiedAccessibility: () => ({
    announceToScreenReader: vi.fn(),
    explicitConfirmations: false,
  }),
}))

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    language: 'en-US',
    t: (key: string, fallback?: string) => fallback ?? key,
  }),
  useLanguage: () => 'en-US',
  I18nProvider: ({ children }: { children: React.ReactNode }) => children,
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

// ---- Helpers -------------------------------------------------------------

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

const FIXTURE_LIST = {
  total: 2,
  items: [
    {
      id: 'aaaa1111-1111-1111-1111-111111111111',
      name: 'Sci-fi 2024+',
      query: 'space',
      filters_json: { item_type: 'book' },
      sort_by: 'relevance',
      view_mode: null,
      notify_on_new: false,
      notify_in_app: true,
      notify_email: false,
      last_run_at: null,
      created_at: '2026-05-16T00:00:00Z',
      updated_at: '2026-05-16T00:00:00Z',
    },
    {
      id: 'bbbb2222-2222-2222-2222-222222222222',
      name: 'New audiobooks',
      query: null,
      filters_json: { item_type: 'audiobook' },
      sort_by: null,
      view_mode: null,
      notify_on_new: true,
      notify_in_app: true,
      notify_email: false,
      last_run_at: null,
      created_at: '2026-05-15T00:00:00Z',
      updated_at: '2026-05-15T00:00:00Z',
    },
  ],
}

beforeEach(() => {
  mocks.apiClient.mockReset()
  // Default: return an empty list so the auto-fetch in SaveThisSearchButton
  // does not emit "Query data cannot be undefined" warnings during dialog
  // tests. Individual tests override with mockResolvedValueOnce.
  mocks.apiClient.mockResolvedValue({ items: [], total: 0 })
})

// ---- Tests ---------------------------------------------------------------

describe('SavedSearchesPanel', () => {
  it('renders rows for each saved search returned by the API', async () => {
    mocks.apiClient.mockResolvedValueOnce(FIXTURE_LIST)
    renderWithClient(<SavedSearchesPanel onRun={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Sci-fi 2024+')).toBeTruthy()
      expect(screen.getByText('New audiobooks')).toBeTruthy()
    })
    expect(mocks.apiClient).toHaveBeenCalledWith('/patrons/me/saved-searches')
  })

  it('shows an empty state when there are no saved searches', async () => {
    mocks.apiClient.mockResolvedValueOnce({ items: [], total: 0 })
    renderWithClient(<SavedSearchesPanel onRun={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByTestId('saved-searches-empty')).toBeTruthy()
    })
  })

  it('fires the onRun callback with the row id when Run is clicked', async () => {
    const onRun = vi.fn()
    mocks.apiClient.mockResolvedValueOnce(FIXTURE_LIST)
    renderWithClient(<SavedSearchesPanel onRun={onRun} />)

    await waitFor(() => expect(screen.getByText('Sci-fi 2024+')).toBeTruthy())
    const runBtn = screen.getByTestId('saved-search-run-aaaa1111-1111-1111-1111-111111111111')
    await userEvent.click(runBtn)
    expect(onRun).toHaveBeenCalledWith('aaaa1111-1111-1111-1111-111111111111')
  })
})

describe('fetchSavedSearch (URL-hydrate boundary)', () => {
  it('GETs the per-id endpoint so ?saved=<id> hydration hits the right route', async () => {
    const { fetchSavedSearch } = await import('../../hooks/useSavedSearches')
    mocks.apiClient.mockResolvedValueOnce(FIXTURE_LIST.items[0])
    const result = await fetchSavedSearch('aaaa1111-1111-1111-1111-111111111111')
    expect(mocks.apiClient).toHaveBeenCalledWith(
      '/patrons/me/saved-searches/aaaa1111-1111-1111-1111-111111111111',
    )
    expect(result.name).toBe('Sci-fi 2024+')
  })
})

describe('SaveThisSearchButton', () => {
  it('renders nothing when there is no active query or filter', () => {
    const { container } = renderWithClient(
      <SaveThisSearchButton
        hasActiveContext={false}
        snapshot={{ query: '', filters: {} }}
      />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('opens the dialog when the button is clicked', async () => {
    renderWithClient(
      <SaveThisSearchButton
        hasActiveContext={true}
        snapshot={{ query: 'space', filters: { item_type: 'book' } }}
      />,
    )
    const button = screen.getByTestId('save-this-search-button')
    await userEvent.click(button)
    expect(screen.getByTestId('save-this-search-dialog')).toBeTruthy()
    expect(screen.getByLabelText(/Name/i)).toBeTruthy()
  })

  it('submits a create request with the snapshot when the form is filled and Save is clicked', async () => {
    mocks.apiClient.mockResolvedValueOnce({
      id: 'cccc3333-3333-3333-3333-333333333333',
      name: 'My space books',
      query: 'space',
      filters_json: { item_type: 'book' },
      sort_by: null,
      view_mode: null,
      notify_on_new: true,
      notify_in_app: true,
      notify_email: false,
      last_run_at: null,
      created_at: '2026-05-16T00:00:00Z',
      updated_at: '2026-05-16T00:00:00Z',
    })

    renderWithClient(
      <SaveThisSearchButton
        hasActiveContext={true}
        snapshot={{ query: 'space', filters: { item_type: 'book' } }}
      />,
    )

    await userEvent.click(screen.getByTestId('save-this-search-button'))
    const input = screen.getByLabelText(/Name/i)
    await userEvent.type(input, 'My space books')
    // Find the "Save" button inside the dialog (not the panel rename "Save").
    const dialog = screen.getByTestId('save-this-search-dialog')
    const saveBtn = Array.from(dialog.querySelectorAll('button')).find(
      (b) => b.textContent?.trim() === 'Save' && b.getAttribute('type') === 'submit',
    )
    expect(saveBtn).toBeTruthy()
    await userEvent.click(saveBtn!)

    await waitFor(() => {
      expect(mocks.apiClient).toHaveBeenCalledWith(
        '/patrons/me/saved-searches',
        expect.objectContaining({
          method: 'POST',
          body: expect.objectContaining({
            name: 'My space books',
            query: 'space',
            filters_json: { item_type: 'book' },
            notify_on_new: true,
            notify_in_app: true,
            notify_email: false,
          }),
        }),
      )
    })
  })
})
