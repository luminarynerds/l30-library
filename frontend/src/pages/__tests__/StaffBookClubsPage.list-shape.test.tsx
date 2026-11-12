/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Regression smoke test for the staff book-clubs admin page.
 *
 * Bug: the page rendered blank because the backend used to return
 * `{ total, book_clubs: [...] }` while the page reads `data.clubs`.
 * This test pins the contract: given an API response with `clubs`,
 * the page renders one row per club.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('../../components/staff/CreateBookClubModal', () => ({
  CreateBookClubModal: () => null,
}))

vi.mock('@/utils/tokenStore', () => ({
  getAccessToken: () => 'test-token',
}))

const mockFetchApi = vi.fn()
vi.mock('@/lib/api-client', () => ({
  fetchApi: (...args: unknown[]) => mockFetchApi(...args),
}))

// Waitlist feature flag OFF here: this regression test only pins the
// list-shape contract; capacity badge / waitlist modal have their own
// dedicated tests.
vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({ isFeatureEnabled: () => false }),
}))

vi.mock('@/i18n', () => ({
  t: (key: string) => key,
}))

// Import after mocks
import StaffBookClubsPage from '../StaffBookClubsPage'

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/staff/admin/book-club']}>
        <StaffBookClubsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  mockFetchApi.mockReset()
})

describe('StaffBookClubsPage list-shape contract', () => {
  it('renders one row per club from the `clubs` key in the API response', async () => {
    mockFetchApi.mockResolvedValueOnce({
      total: 2,
      clubs: [
        {
          id: 1,
          name: 'Tuesday Mystery Readers',
          description: 'Cozy mysteries, weekly.',
          status: 'active',
          max_members: 12,
          is_public: true,
          meeting_frequency: 'weekly',
          members: [{ id: 10 }, { id: 11 }],
          meetings: [],
        },
        {
          id: 2,
          name: 'Memoir Circle',
          description: null,
          status: 'draft',
          max_members: null,
          is_public: false,
          meeting_frequency: 'monthly',
          members: [],
          meetings: [],
        },
      ],
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Tuesday Mystery Readers')).toBeInTheDocument()
      expect(screen.getByText('Memoir Circle')).toBeInTheDocument()
    })

    // Pin the staff endpoint: `/book-clubs` (no slash) resolves to the patron
    // router and returns a reduced public-only shape. The staff list must hit
    // `/book-clubs/` (trailing slash).
    expect(mockFetchApi).toHaveBeenCalledWith('/book-clubs/', expect.anything())
  })

  it('renders zero rows when the API returns the legacy `book_clubs` key', async () => {
    // Guardrail: if the backend regresses to `book_clubs`, the page should
    // render zero rows, surfacing the contract break in CI rather than
    // silently going blank in prod.
    mockFetchApi.mockResolvedValueOnce({
      total: 1,
      book_clubs: [
        {
          id: 99,
          name: 'Should Not Appear',
          description: null,
          status: 'active',
          max_members: null,
          is_public: true,
          meeting_frequency: null,
          members: [],
          meetings: [],
        },
      ],
    })

    renderPage()

    await waitFor(() => {
      expect(mockFetchApi).toHaveBeenCalled()
    })
    expect(screen.queryByText('Should Not Appear')).not.toBeInTheDocument()
  })
})
