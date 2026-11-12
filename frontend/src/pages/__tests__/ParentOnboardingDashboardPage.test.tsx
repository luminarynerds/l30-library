/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * A11y/UX smoke tests for ParentOnboardingDashboardPage:
 *   - loading state renders inside AdminShell (nav stays put on slow loads)
 *   - error state renders inside AdminShell (nav stays put on failed loads)
 *   - risk pill has aria-label with explicit "Risk level: high - urgent"
 *   - urgent overdue StatCard exposes an "urgent" accessible label
 *   - stats grid is wrapped in aria-live polite for screen-reader updates
 *   - refresh button awaits refetch and surfaces error toast on failure
 *   - Up Next rail renders three buckets, scoped to signed-in coordinator,
 *     with accessible row names and stable focus order
 *   - Overdue risk-filter toggle: filters the rail's Overdue bucket
 *     (aria-pressed, persistence, empty state, polite live announcement)
 */
import { describe, it, expect, vi, beforeEach, beforeAll, afterAll } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

// src/__tests__/setup.ts mocks window.localStorage as bare vi.fn() stubs that
// don't store anything. Replace with a real Map-backed shim so the risk-filter
// persistence assertions hit actual storage behavior.
let __testStorage: Map<string, string>
let __origLocalStorage: Storage
beforeAll(() => {
  __origLocalStorage = window.localStorage
  __testStorage = new Map<string, string>()
  const shim: Storage = {
    get length() { return __testStorage.size },
    clear: () => __testStorage.clear(),
    getItem: (k: string) => (__testStorage.has(k) ? __testStorage.get(k)! : null),
    setItem: (k: string, v: string) => { __testStorage.set(k, String(v)) },
    removeItem: (k: string) => { __testStorage.delete(k) },
    key: (i: number) => Array.from(__testStorage.keys())[i] ?? null,
  }
  Object.defineProperty(window, 'localStorage', { value: shim, configurable: true })
})
afterAll(() => {
  Object.defineProperty(window, 'localStorage', { value: __origLocalStorage, configurable: true })
})

const mocks = vi.hoisted(() => ({
  getDashboard: vi.fn(),
  triggerWeeklySummaryDownload: vi.fn(),
}))

vi.mock('@/api/parent-onboarding-api', () => mocks)

const toastMocks = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  loading: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: toastMocks,
  __esModule: true,
}))

// Minimal catalog the page actually depends on for assertions. Other keys fall
// through to fallback strings, mirroring the production t(key, fallback) shape.
const TEST_CATALOG: Record<string, string> = {
  'parentOnboarding.dashboard.overdue.filter.announce':
    'Showing {count} {level} overdue check-ins.',
}

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (k: string, paramsOrFallback?: Record<string, unknown> | string) => {
      const fromCatalog = TEST_CATALOG[k]
      if (typeof paramsOrFallback === 'string') {
        // Fallback string: prefer catalog if present, else literal fallback.
        return fromCatalog ?? paramsOrFallback
      }
      // Params object (or undefined): substitute against catalog string, else
      // return the raw key (no fallback was provided).
      const base = fromCatalog ?? k
      if (paramsOrFallback && typeof paramsOrFallback === 'object') {
        let out = base
        for (const [pk, pv] of Object.entries(paramsOrFallback)) {
          out = out.split('{' + pk + '}').join(String(pv)).split('{{' + pk + '}}').join(String(pv))
        }
        return out
      }
      return base
    },
    language: 'en',
    isRTL: false,
    setLanguage: vi.fn(),
  }),
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

// useAuth provides the signed-in coordinator id; the Up Next rail filters by it.
const COORDINATOR_ID = 200
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: COORDINATOR_ID, email: 'coord@example.com', is_active: true, is_verified: true, full_name: 'Coord' },
    token: 'test-token',
    isAuthenticated: true,
    isLoading: false,
    sessionExpired: false,
    sessionStartTime: new Date(),
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    refreshUser: vi.fn(),
    updateProfile: vi.fn(),
    loginWithMagicLink: vi.fn(),
    completeLogin: vi.fn(),
    clearSessionExpired: vi.fn(),
    getSessionDuration: () => null,
  }),
}))

// AdminShell pulls in StaffLayout → mock so we don't drag the whole shell graph.
// Stamp a stable testid so the loading/error assertions can verify the wrapper.
vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div data-testid="admin-shell" data-title={title}>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}))

import ParentOnboardingDashboardPage from '../ParentOnboardingDashboardPage'
import { STORAGE_KEY } from '../../hooks/useParentOnboardingDashboardPrefs'

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  )
}

// Build fixture dates relative to the wall-clock so tests stay valid regardless
// of when they run. Browser-local YYYY-MM-DD via en-CA matches what the rail
// uses internally.
function localISODate(d: Date): string {
  return d.toLocaleDateString('en-CA')
}
function offsetDays(d: Date, days: number): Date {
  const out = new Date(d)
  out.setDate(out.getDate() + days)
  return out
}
const NOW = new Date()
const TODAY = localISODate(NOW)
const YESTERDAY_2 = localISODate(offsetDays(NOW, -3)) // overdue
const TOMORROW = localISODate(offsetDays(NOW, 1)) // this week
const TOMORROW_2 = localISODate(offsetDays(NOW, 3)) // this week

const dashboardFixture = {
  active_families: 12,
  upcoming_sessions: 4,
  overdue_check_ins: 3,
  active_childcare_sessions: 2,
  active_connection_groups: 5,
  pending_enrollments: 1,
  upcoming_home_visits: 2,
  // Summary shape (ParentOnboardingSessionSummary): owner is staff_id and
  // scheduled_date is a full ISO datetime -- there is no scheduled_time field.
  recent_sessions: [
    {
      id: 50,
      patron_id: 500,
      patron_name: 'Today Patron',
      staff_id: COORDINATOR_ID,
      status: 'scheduled',
      scheduled_date: `${TODAY}T09:30:00`,
    },
    {
      id: 51,
      patron_id: 501,
      patron_name: 'Other Coordinator Patron',
      staff_id: 999, // different staff member: must NOT appear
      status: 'scheduled',
      scheduled_date: `${TODAY}T10:00:00`,
    },
  ],
  overdue_assignments: [
    {
      id: 1,
      patron_id: 100,
      patron_name: 'High Risk Parent',
      coordinator_id: COORDINATOR_ID,
      status: 'active',
      risk_level: 'high',
      check_in_frequency: 'weekly',
      assigned_at: '2026-05-01',
      next_check_in_due: YESTERDAY_2, // overdue
      total_check_ins: 0,
    },
    {
      id: 2,
      patron_id: 101,
      patron_name: 'Medium Risk Parent',
      coordinator_id: COORDINATOR_ID,
      status: 'active',
      risk_level: 'medium',
      check_in_frequency: 'monthly',
      assigned_at: '2026-05-01',
      next_check_in_due: TOMORROW_2, // this week
      total_check_ins: 1,
    },
  ],
  upcoming_visits: [
    {
      id: 30,
      patron_id: 300,
      patron_name: 'Visit Patron',
      visitor_id: COORDINATOR_ID,
      purpose: 'check_in',
      status: 'scheduled',
      scheduled_date: TOMORROW, // this week
      scheduled_time: '14:00',
      follow_up_needed: false,
      created_at: '2026-05-01T00:00:00',
    },
  ],
}

// Filter-specific fixture: 2 assignments BOTH overdue (date < today) so the
// rail's overdue bucket contains 1 high + 1 medium. The risk-filter toggle
// then has something to filter (1 of 2 → 1). The base `dashboardFixture` only
// has 1 overdue assignment, so the toggle would be a no-op there.
function makeFilterFixture(overrides: Partial<typeof dashboardFixture> = {}) {
  return {
    ...dashboardFixture,
    recent_sessions: [],
    upcoming_visits: [],
    overdue_assignments: [
      {
        id: 11,
        patron_id: 110,
        patron_name: 'Filter High Parent',
        coordinator_id: COORDINATOR_ID,
        status: 'active',
        risk_level: 'high',
        check_in_frequency: 'weekly',
        assigned_at: '2026-05-01',
        next_check_in_due: YESTERDAY_2, // overdue
        total_check_ins: 0,
      },
      {
        id: 12,
        patron_id: 111,
        patron_name: 'Filter Medium Parent',
        coordinator_id: COORDINATOR_ID,
        status: 'active',
        risk_level: 'medium',
        check_in_frequency: 'monthly',
        assigned_at: '2026-05-01',
        next_check_in_due: YESTERDAY_2, // also overdue
        total_check_ins: 1,
      },
    ],
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  __testStorage.clear()
  mocks.getDashboard.mockResolvedValue(dashboardFixture)
})

describe('ParentOnboardingDashboardPage a11y', () => {
  it('renders loading state inside AdminShell so staff keep the nav', async () => {
    // Hold the query open: never resolves during this test.
    mocks.getDashboard.mockImplementation(() => new Promise(() => {}))
    wrap(<ParentOnboardingDashboardPage />)
    const shell = await screen.findByTestId('admin-shell')
    expect(shell).toBeInTheDocument()
    expect(shell.getAttribute('data-title')).toBe('Parent Onboarding')
    // Loading region announces itself to screen readers.
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite')
  })

  it('renders error state inside AdminShell so staff keep the nav', async () => {
    mocks.getDashboard.mockRejectedValue(new Error('boom'))
    wrap(<ParentOnboardingDashboardPage />)
    const shell = await screen.findByTestId('admin-shell')
    expect(shell).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Failed to load dashboard data')).toBeInTheDocument()
  })

  it('risk pill exposes "Risk level: high - urgent" via aria-label', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const highPill = await screen.findByLabelText('Risk level: high - urgent')
    expect(highPill).toBeInTheDocument()
    // Medium does not get the "urgent" suffix.
    expect(screen.getByLabelText('Risk level: medium')).toBeInTheDocument()
  })

  it('urgent overdue stat card carries an "urgent" accessible label', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const urgentCard = await screen.findByLabelText(/Overdue Check-ins: 3 - urgent/)
    expect(urgentCard).toBeInTheDocument()
  })

  it('stats grid is wrapped in an aria-live polite region', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const region = await screen.findByLabelText('Dashboard statistics')
    expect(region).toHaveAttribute('aria-live', 'polite')
  })

  it('refresh button awaits refetch and shows error toast on failure', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    await screen.findByLabelText('Dashboard statistics')

    // Next call rejects: refresh should NOT claim success.
    mocks.getDashboard.mockRejectedValueOnce(new Error('network down'))
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /Refresh/i }))

    await waitFor(() => expect(toastMocks.error).toHaveBeenCalledWith('Failed to refresh dashboard'))
    expect(toastMocks.success).not.toHaveBeenCalled()
  })

  it('refresh button shows success toast only after refetch resolves', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    await screen.findByLabelText('Dashboard statistics')

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /Refresh/i }))

    await waitFor(() => expect(toastMocks.success).toHaveBeenCalledWith('Dashboard refreshed'))
  })
})

describe('ParentOnboardingDashboardPage Up Next rail', () => {
  it('renders the Up Next rail as a labelled landmark with aria-live polite', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const heading = await screen.findByRole('heading', { name: /Up Next/i, level: 2 })
    const rail = heading.closest('section')
    expect(rail).not.toBeNull()
    expect(rail).toHaveAttribute('aria-live', 'polite')
    expect(rail).toHaveAttribute('aria-labelledby', 'up-next-heading')
    expect(heading).toHaveAttribute('id', 'up-next-heading')
  })

  it('renders Overdue, Today, and This Week sub-headings with visible counts', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const overdueHeading = await screen.findByRole('heading', { name: /Overdue/i, level: 3 })
    const todayHeading = screen.getByRole('heading', { name: /^Today/i, level: 3 })
    const weekHeading = screen.getByRole('heading', { name: /This Week/i, level: 3 })
    // Counts are visible text inside the heading, not aria-label only.
    expect(overdueHeading.textContent).toMatch(/\(1\)/) // 1 overdue assignment
    expect(todayHeading.textContent).toMatch(/\(1\)/) // 1 session today
    expect(weekHeading.textContent).toMatch(/\(2\)/) // 1 assignment + 1 visit
  })

  it('filters rows by coordinator scope so other coordinators do not appear', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    await screen.findByRole('heading', { name: /Up Next/i, level: 2 })
    // The "Other Coordinator Patron" session belongs to coordinator 999 → must NOT be on this rail.
    expect(screen.queryByText(/Other Coordinator Patron/)).not.toBeInTheDocument()
  })

  it('each rail row is a focusable link whose accessible name carries entity + patron', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    await screen.findByRole('heading', { name: /Up Next/i, level: 2 })

    const overdueLink = screen.getByRole('link', { name: /Check-in - High Risk Parent/i })
    expect(overdueLink).toHaveAttribute('href', '/staff/parent-onboarding/care-assignments/1')

    const todayLink = screen.getByRole('link', { name: /Session - Today Patron/i })
    expect(todayLink).toHaveAttribute('href', '/staff/parent-onboarding/sessions/50')

    const visitLink = screen.getByRole('link', { name: /Home visit - Visit Patron/i })
    expect(visitLink).toHaveAttribute('href', '/staff/parent-onboarding/home-visits/30')
  })

  it('renders the bucket empty-state text when a bucket has no items', async () => {
    mocks.getDashboard.mockResolvedValueOnce({
      ...dashboardFixture,
      recent_sessions: [],
      overdue_assignments: [],
      upcoming_visits: [],
    })
    wrap(<ParentOnboardingDashboardPage />)
    expect(await screen.findByText('Nothing overdue. Nice work.')).toBeInTheDocument()
    expect(screen.getByText('Nothing scheduled today.')).toBeInTheDocument()
    expect(screen.getByText('Nothing scheduled this week.')).toBeInTheDocument()
  })

  it('focus order: Overdue links precede Today links precede This Week links', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const rail = (await screen.findByRole('heading', { name: /Up Next/i, level: 2 })).closest('section')
    expect(rail).not.toBeNull()
    const links = within(rail!).getAllByRole('link')
    const labels = links.map((l) => l.getAttribute('aria-label') ?? '')
    expect(labels[0]).toMatch(/Check-in - High Risk Parent/i)
    expect(labels[1]).toMatch(/Session - Today Patron/i)
    // Last two are This Week items.
    expect(labels.slice(2).join(' ')).toMatch(/Medium Risk Parent/i)
    expect(labels.slice(2).join(' ')).toMatch(/Visit Patron/i)
  })
})

describe('ParentOnboardingDashboardPage overdue risk filter', () => {
  beforeEach(() => {
    // Filter tests need 2 overdue assignments (1 high, 1 medium) in
    // buckets.overdue so the toggle has something to filter from.
    mocks.getDashboard.mockResolvedValue(makeFilterFixture())
  })

  it('renders both pills with their unfiltered counts and "All" pressed by default', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const allBtn = await screen.findByRole('button', { name: /^All \(2\)$/ })
    const highBtn = screen.getByRole('button', { name: /^High risk only \(1\)$/ })
    expect(allBtn).toHaveAttribute('aria-pressed', 'true')
    expect(highBtn).toHaveAttribute('aria-pressed', 'false')
  })

  it('shows all overdue rows by default', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    await screen.findByRole('button', { name: /^All \(2\)$/ })
    expect(screen.getByText('Filter High Parent')).toBeInTheDocument()
    expect(screen.getByText('Filter Medium Parent')).toBeInTheDocument()
  })

  it('filters the rail Overdue bucket to risk_level === "high" when "High risk only" is selected', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const highBtn = await screen.findByRole('button', { name: /^High risk only \(1\)$/ })
    const user = userEvent.setup()
    await user.click(highBtn)
    expect(highBtn).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /^All \(2\)$/ })).toHaveAttribute('aria-pressed', 'false')
    // Only the high-risk row is left.
    expect(screen.getByText('Filter High Parent')).toBeInTheDocument()
    expect(screen.queryByText('Filter Medium Parent')).not.toBeInTheDocument()
  })

  it('persists the selection to localStorage on toggle', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const highBtn = await screen.findByRole('button', { name: /^High risk only \(1\)$/ })
    const user = userEvent.setup()
    await user.click(highBtn)
    await waitFor(() => {
      const raw = window.localStorage.getItem(STORAGE_KEY)
      expect(raw).toBeTruthy()
      expect(JSON.parse(raw!)).toEqual({ overdueRiskFilter: 'high' })
    })
  })

  it('hydrates from localStorage on mount (persisted filter survives reload)', async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ overdueRiskFilter: 'high' }),
    )
    wrap(<ParentOnboardingDashboardPage />)
    const highBtn = await screen.findByRole('button', { name: /^High risk only \(1\)$/ })
    expect(highBtn).toHaveAttribute('aria-pressed', 'true')
    expect(screen.queryByText('Filter Medium Parent')).not.toBeInTheDocument()
  })

  it('renders the empty-state hint + "Show all" link when high-only filter yields zero results', async () => {
    // Override: 1 medium overdue, 0 high.
    mocks.getDashboard.mockResolvedValue(
      makeFilterFixture({
        overdue_assignments: [
          {
            id: 99,
            patron_id: 199,
            patron_name: 'Lone Medium Parent',
            coordinator_id: COORDINATOR_ID,
            status: 'active',
            risk_level: 'medium',
            check_in_frequency: 'monthly',
            assigned_at: '2026-05-01',
            next_check_in_due: YESTERDAY_2,
            total_check_ins: 1,
          },
        ],
      }),
    )
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ overdueRiskFilter: 'high' }),
    )
    wrap(<ParentOnboardingDashboardPage />)
    expect(await screen.findByText('No high-risk overdue check-ins.')).toBeInTheDocument()
    const showAll = screen.getByRole('button', { name: 'Show all overdue' })
    expect(showAll).toBeInTheDocument()

    const user = userEvent.setup()
    await user.click(showAll)
    expect(screen.getByRole('button', { name: /^All \(1\)$/ })).toHaveAttribute('aria-pressed', 'true')
  })

  it('updates the overdue-filter polite live region when the filter changes', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const region = await screen.findByTestId('overdue-filter-announce')
    expect(region).toHaveAttribute('aria-live', 'polite')
    // Initial state: announces "all" count.
    expect(region.textContent ?? '').toMatch(/Showing\b/)
    const initial = region.textContent

    const highBtn = screen.getByRole('button', { name: /^High risk only \(1\)$/ })
    const user = userEvent.setup()
    await user.click(highBtn)
    // Content changes after filter flip (count drops 2 -> 1).
    await waitFor(() => {
      expect(region.textContent).not.toBe(initial)
    })
  })

  it('does not render the filter toggle when no assignments land in the rail overdue bucket', async () => {
    mocks.getDashboard.mockResolvedValue(
      makeFilterFixture({ overdue_assignments: [] }),
    )
    wrap(<ParentOnboardingDashboardPage />)
    // Empty rail-overdue shows the bucket's empty-state copy and no toggle.
    expect(await screen.findByText('Nothing overdue. Nice work.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^All / })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^High risk only / })).not.toBeInTheDocument()
  })

  it('toggle button is keyboard-focusable (Tab reaches it)', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const highBtn = await screen.findByRole('button', { name: /^High risk only \(1\)$/ })
    highBtn.focus()
    expect(highBtn).toHaveFocus()
  })

  it('stat-card aria-live region for stats remains intact after filter activation', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const stats = await screen.findByLabelText('Dashboard statistics')
    const highBtn = screen.getByRole('button', { name: /^High risk only \(1\)$/ })
    const user = userEvent.setup()
    await user.click(highBtn)
    // The stats live region survives the filter flip — it's a separate concern.
    expect(stats).toHaveAttribute('aria-live', 'polite')
    expect(within(stats).getByText('Active Families')).toBeInTheDocument()
  })
})

describe('ParentOnboardingDashboardPage weekly export menu', () => {
  beforeEach(() => {
    mocks.getDashboard.mockReset()
    mocks.getDashboard.mockResolvedValue(dashboardFixture)
    mocks.triggerWeeklySummaryDownload.mockReset()
    mocks.triggerWeeklySummaryDownload.mockResolvedValue({
      filename: 'parent-onboarding-weekly-2026-05-25.csv',
    })
    toastMocks.success.mockReset()
    toastMocks.error.mockReset()
    toastMocks.loading.mockReset()
  })

  it('renders an Export weekly summary button with aria-haspopup="menu"', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const btn = await screen.findByRole('button', { name: /Export weekly summary/i })
    expect(btn).toHaveAttribute('aria-haspopup', 'menu')
    expect(btn).toHaveAttribute('aria-expanded', 'false')
  })

  it('opens the menu on click and exposes CSV + PDF + mineOnly toggle', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const btn = await screen.findByRole('button', { name: /Export weekly summary/i })
    const user = userEvent.setup()
    await user.click(btn)

    expect(btn).toHaveAttribute('aria-expanded', 'true')
    const menu = screen.getByRole('menu', { name: /Export weekly summary/i })
    const items = within(menu).getAllByRole('menuitem')
    // CSV item is enabled, PDF item is disabled.
    const csvItem = within(menu).getByRole('menuitem', {
      name: /Download as CSV \(last 7 days\)/i,
    })
    const pdfItem = within(menu).getByRole('menuitem', {
      name: /Download as PDF \(last 7 days\)/i,
    })
    expect(csvItem).toBeEnabled()
    expect(pdfItem).toBeDisabled()
    expect(items).toHaveLength(2)
    // mineOnly toggle is a checkbox, not a menuitem, but it must be in the menu.
    expect(within(menu).getByRole('checkbox')).not.toBeChecked()
  })

  it('CSV menuitem triggers downloadWeeklySummary with format=csv and surfaces success toast', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const btn = await screen.findByRole('button', { name: /Export weekly summary/i })
    const user = userEvent.setup()
    await user.click(btn)
    await user.click(
      screen.getByRole('menuitem', { name: /Download as CSV \(last 7 days\)/i }),
    )
    await waitFor(() =>
      expect(mocks.triggerWeeklySummaryDownload).toHaveBeenCalledWith(
        expect.objectContaining({ format: 'csv' }),
      ),
    )
    // Loading toast fired first.
    expect(toastMocks.loading).toHaveBeenCalled()
    await waitFor(() => expect(toastMocks.success).toHaveBeenCalled())
  })

  it('mineOnly toggle appends coordinator_id=me to the request', async () => {
    wrap(<ParentOnboardingDashboardPage />)
    const btn = await screen.findByRole('button', { name: /Export weekly summary/i })
    const user = userEvent.setup()
    await user.click(btn)
    await user.click(screen.getByRole('checkbox'))
    await user.click(
      screen.getByRole('menuitem', { name: /Download as CSV \(last 7 days\)/i }),
    )
    await waitFor(() =>
      expect(mocks.triggerWeeklySummaryDownload).toHaveBeenCalledWith(
        expect.objectContaining({ format: 'csv', coordinatorId: 'me' }),
      ),
    )
  })

  it('download failure surfaces error toast', async () => {
    mocks.triggerWeeklySummaryDownload.mockRejectedValueOnce(
      new Error('boom'),
    )
    wrap(<ParentOnboardingDashboardPage />)
    const btn = await screen.findByRole('button', { name: /Export weekly summary/i })
    const user = userEvent.setup()
    await user.click(btn)
    await user.click(
      screen.getByRole('menuitem', { name: /Download as CSV \(last 7 days\)/i }),
    )
    await waitFor(() => expect(toastMocks.error).toHaveBeenCalled())
    expect(toastMocks.success).not.toHaveBeenCalled()
  })
})
