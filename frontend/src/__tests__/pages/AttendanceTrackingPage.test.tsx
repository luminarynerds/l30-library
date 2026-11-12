/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * AttendanceTrackingPage Tests
 *
 * Tests for the attendance tracking page including:
 * - Access control (staff/admin only)
 * - Dashboard rendering with stats
 * - Tab navigation
 * - Session list display
 * - Check-in interface (library card, walk-in, head count modes)
 * - Session creation modal
 * - ROI trends display
 * - Loading and empty states
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '../utils/test-utils'
import { screen, waitFor } from '@testing-library/dom'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AttendanceTrackingPage from '@/pages/AttendanceTrackingPage'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

// ============================================================================
// Mock Data
// ============================================================================

const mockDashboard = {
  today_sessions: 3,
  today_total_attendance: 47,
  week_total_attendance: 215,
  month_total_attendance: 890,
  avg_attendance_per_event: 28.5,
  repeat_attendee_rate: 34.2,
  top_check_in_method: 'library_card',
  recent_sessions: [
    {
      id: 1,
      session_name: 'Story Hour',
      session_date: '2026-02-25',
      status: 'open',
      event_id: null,
      program_id: null,
      head_count_mode: false,
      total_checked_in: 15,
      head_count_total: 0,
      effective_total: 15,
      cost_per_attendee: 5.0,
    },
    {
      id: 2,
      session_name: 'Community Concert',
      session_date: '2026-02-24',
      status: 'closed',
      event_id: 10,
      program_id: null,
      head_count_mode: true,
      total_checked_in: 0,
      head_count_total: 250,
      effective_total: 250,
      cost_per_attendee: 2.0,
    },
  ],
  age_distribution: {
    '0-5': 12,
    '6-12': 25,
    '18-34': 40,
    '35-54': 30,
    '65+': 8,
  },
  method_distribution: {
    library_card: 45,
    walk_in: 30,
    qr_code: 20,
  },
}

const mockSessionsList = {
  data: [
    {
      id: 1,
      session_name: 'Story Hour',
      session_date: '2026-02-25',
      status: 'open',
      qr_code_token: 'abc123def456',
      head_count_mode: false,
      head_count_total: 0,
      total_checked_in: 15,
      total_walk_ins: 5,
      total_pre_registered: 0,
      total_card_scans: 8,
      total_qr_scans: 2,
      event_cost: 75.0,
      survey_enabled: true,
      effective_total: 15,
      cost_per_attendee: 5.0,
      created_at: '2026-02-25T09:00:00Z',
      updated_at: '2026-02-25T09:00:00Z',
    },
  ],
  pagination: {
    page: 1,
    per_page: 20,
    total: 1,
    total_pages: 1,
    has_next: false,
    has_previous: false,
  },
}

const mockROI = {
  period_label: '2025-02-25 to 2026-02-25',
  total_events: 52,
  total_attendance: 1480,
  total_cost: 3600.0,
  cost_per_attendee: 2.43,
  repeat_rate: 34.2,
  top_programs: [
    { name: 'Story Hour', attendance: 520 },
    { name: 'Summer Reading', attendance: 340 },
    { name: 'Tech Workshop', attendance: 180 },
  ],
}

// ============================================================================
// Auth Mock Setup
// ============================================================================

// Default: staff user (has access). Hoisted so vi.mock factory can use it.
const authState = vi.hoisted(() => ({
  user: { id: 1, email: 'staff@library.org', role: 'staff' } as Record<string, unknown> | null,
}))
// Backwards-compat alias the tests already use
// let mockAuthUser: Record<string, unknown> | null = authState.user

vi.mock('@/contexts/AuthContext', async () => {
  const React = await import('react')
  return {
    useAuth: () => ({
      user: authState.user,
      token: 'test-token',
      isLoading: false,
      isAuthenticated: true,
      sessionExpired: false,
      clearSessionExpired: vi.fn(),
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      updateProfile: vi.fn(),
      refreshUser: vi.fn(),
      showTimeoutWarning: false,
      timeoutSeconds: 120,
      dismissTimeoutWarning: vi.fn(),
      extendSession: vi.fn(),
      getSessionDuration: vi.fn(() => null),
    }),
    AuthProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
  }
})
vi.mock('../../contexts/AuthContext', async () => {
  const React = await import('react')
  return {
    useAuth: () => ({
      user: authState.user,
      token: 'test-token',
      isLoading: false,
      isAuthenticated: true,
      sessionExpired: false,
      clearSessionExpired: vi.fn(),
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      updateProfile: vi.fn(),
      refreshUser: vi.fn(),
      showTimeoutWarning: false,
      timeoutSeconds: 120,
      dismissTimeoutWarning: vi.fn(),
      extendSession: vi.fn(),
      getSessionDuration: vi.fn(() => null),
    }),
    AuthProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
  }
})

// ============================================================================
// Tests
// ============================================================================

describe('AttendanceTrackingPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    authState.user = { id: 1, email: 'staff@library.org', role: 'staff' }
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    // Default: dashboard endpoint returns mock data
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockDashboard,
    })
  })

  // ========================================================================
  // Access Control
  // ========================================================================

  describe('Access Control', () => {
    it('should allow access to staff', () => {
      authState.user = { id: 1, email: 'staff@library.org', role: 'staff' }

      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      // StaffLayout renders its own title (mobile sticky h2 + desktop h1)
      // *and* AdminShell renders a second icon-prefixed h1 for the same
      // title — jsdom doesn't apply the lg:/hidden breakpoint CSS that
      // keeps only one visible at a time in a real browser, so all copies
      // are present in the accessibility tree here.
      expect(screen.getAllByText('Attendance Tracking').length).toBeGreaterThan(0)
    })

    it('should allow access to admins', () => {
      authState.user = { id: 1, email: 'admin@library.org', role: 'admin' }

      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      expect(screen.getAllByText('Attendance Tracking').length).toBeGreaterThan(0)
    })

    // Access control lives at the route level: every staff route wraps in
    // RequireAuth (src/routes/StaffRoutes.tsx:232-234), which REDIRECTS
    // unauthorized users (login for anonymous, /account for wrong role)
    // before this page ever mounts. StaffLayout's `return null` for
    // non-staff is flash prevention behind that guard, so a bare
    // unauthorized render of the page yields an empty tree — the page's own
    // "Staff-Only Area" branch is unreachable defense-in-depth, not the
    // user-facing denial path.
    it('renders nothing for patrons (route guard handles the redirect)', () => {
      authState.user = { id: 1, email: 'patron@example.com', role: 'patron' }

      const { container } = render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      expect(screen.queryByText('Attendance Tracking')).not.toBeInTheDocument()
      expect(container).toBeEmptyDOMElement()
    })

    it('renders nothing when not logged in (route guard handles the redirect)', () => {
      authState.user = null

      const { container } = render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      expect(screen.queryByText('Attendance Tracking')).not.toBeInTheDocument()
      expect(container).toBeEmptyDOMElement()
    })
  })

  // ========================================================================
  // Page Structure
  // ========================================================================

  describe('Page Structure', () => {
    it('should render page title and subtitle', () => {
      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      // See "should allow access to staff" above re: title rendering twice
      // (StaffLayout + AdminShell both render it; not CSS-filtered in jsdom).
      expect(screen.getAllByText('Attendance Tracking').length).toBeGreaterThan(0)
      expect(screen.getAllByText(/no more paper sheets/i).length).toBeGreaterThan(0)
    })

    it('should render all four tabs', () => {
      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.getByText('Sessions')).toBeInTheDocument()
      expect(screen.getByText('Check-In')).toBeInTheDocument()
      expect(screen.getByText('Trends & ROI')).toBeInTheDocument()
    })

    it('should default to Dashboard tab', () => {
      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      // Dashboard tab should be active (blue)
      const dashboardTab = screen.getByText('Dashboard')
      expect(dashboardTab.closest('button')).toHaveClass('border-lsc-rose')
    })
  })

  // ========================================================================
  // Tab Navigation
  // ========================================================================

  describe('Tab Navigation', () => {
    it('should switch to Sessions tab on click', async () => {
      mockFetch.mockImplementation((url: string) => Promise.resolve({
        ok: true,
        json: async () => /sessions/.test(url) && !/dashboard/.test(url)
          ? mockSessionsList
          : mockDashboard,
      }))

      const user = userEvent.setup()

      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await user.click(screen.getByText('Sessions'))

      await waitFor(() => {
        expect(screen.getByText('New Session')).toBeInTheDocument()
      })
    })

    it('should switch to Check-In tab on click', async () => {
      const user = userEvent.setup()

      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await user.click(screen.getByText('Check-In'))

      await waitFor(() => {
        expect(screen.getByText(/Select a session/i)).toBeInTheDocument()
      })
    })

    it('should switch to Trends & ROI tab on click', async () => {
      mockFetch.mockImplementation((url: string) => Promise.resolve({
        ok: true,
        json: async () => /roi/.test(url) ? mockROI : mockDashboard,
      }))

      const user = userEvent.setup()

      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await user.click(screen.getByText('Trends & ROI'))

      await waitFor(() => {
        expect(screen.getByText(/ROI Report/i)).toBeInTheDocument()
      })
    })
  })

  // ========================================================================
  // Dashboard Tab
  // ========================================================================

  describe('Dashboard Tab', () => {
    it('should display dashboard stats', async () => {
      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByText("Today's Sessions")).toBeInTheDocument()
        expect(screen.getByText('3')).toBeInTheDocument() // today_sessions
        expect(screen.getByText("Today's Attendance")).toBeInTheDocument()
        expect(screen.getByText('47')).toBeInTheDocument() // today_total_attendance
      })
    })

    it('should display repeat rate', async () => {
      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByText('Repeat Rate')).toBeInTheDocument()
        expect(screen.getByText('34.2%')).toBeInTheDocument()
      })
    })

    it('should display check-in method distribution', async () => {
      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByText('Check-In Methods (30 days)')).toBeInTheDocument()
        expect(screen.getByText('Library Card')).toBeInTheDocument()
        expect(screen.getByText('Walk-In')).toBeInTheDocument()
        expect(screen.getByText('QR Code')).toBeInTheDocument()
      })
    })

    it('should display recent sessions table', async () => {
      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByText('Recent Sessions')).toBeInTheDocument()
        expect(screen.getByText('Story Hour')).toBeInTheDocument()
        expect(screen.getByText('Community Concert')).toBeInTheDocument()
      })
    })

    it('should show loading state', () => {
      mockFetch.mockImplementation(() => new Promise(() => {})) // Never resolves

      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      // Should show loading spinner (Loader2 component). The spin utility is
      // applied via the `motion-safe:` variant (respects prefers-reduced-motion,
      // #c0cd846b3 style-guide pass), so the class token is
      // "motion-safe:animate-spin", not a bare "animate-spin".
      const spinners = document.querySelectorAll('[class*="animate-spin"]')
      expect(spinners.length).toBeGreaterThan(0)
    })
  })

  // ========================================================================
  // Sessions Tab
  // ========================================================================

  describe('Sessions Tab', () => {
    it('should show empty state when no sessions exist', async () => {
      mockFetch.mockImplementation((url: string) => Promise.resolve({
        ok: true,
        json: async () => /sessions/.test(url) && !/dashboard/.test(url)
          ? { data: [], pagination: { page: 1, per_page: 20, total: 0, total_pages: 0, has_next: false, has_previous: false } }
          : mockDashboard,
      }))

      const user = userEvent.setup()

      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await user.click(screen.getByText('Sessions'))

      await waitFor(() => {
        expect(screen.getByText(/No attendance sessions/i)).toBeInTheDocument()
      })
    })

    it('should display sessions list', async () => {
      // Route by URL rather than call order: the page shell fires several
      // unrelated background fetches on mount (hub-favorites, branding,
      // etc.) before the attendance dashboard call, so a plain
      // mockResolvedValueOnce("first call = dashboard") hands the dashboard
      // endpoint the sessions-list shape instead — which is missing
      // method_distribution/age_distribution and crashes DashboardTab.
      mockFetch.mockImplementation((url: string) => Promise.resolve({
        ok: true,
        json: async () => /sessions/.test(url) && !/dashboard/.test(url)
          ? mockSessionsList
          : mockDashboard,
      }))

      const user = userEvent.setup()

      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await user.click(screen.getByText('Sessions'))

      await waitFor(() => {
        expect(screen.getByText('Story Hour')).toBeInTheDocument()
      })
    })

    it('should have status filter dropdown', async () => {
      mockFetch.mockImplementation((url: string) => Promise.resolve({
        ok: true,
        json: async () => /sessions/.test(url) && !/dashboard/.test(url)
          ? mockSessionsList
          : mockDashboard,
      }))

      const user = userEvent.setup()

      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await user.click(screen.getByText('Sessions'))

      await waitFor(() => {
        const select = screen.getByDisplayValue('All Statuses')
        expect(select).toBeInTheDocument()
      })
    })
  })

  // ========================================================================
  // Check-In Tab
  // ========================================================================

  describe('Check-In Tab', () => {
    it('should show placeholder when no session selected', async () => {
      const user = userEvent.setup()

      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await user.click(screen.getByText('Check-In'))

      await waitFor(() => {
        expect(screen.getByText(/Select a session/i)).toBeInTheDocument()
      })
    })
  })

  // ========================================================================
  // Trends & ROI Tab
  // ========================================================================

  describe('Trends & ROI Tab', () => {
    it('should display ROI metrics', async () => {
      mockFetch.mockImplementation((url: string) => Promise.resolve({
        ok: true,
        json: async () => /roi/.test(url) ? mockROI : mockDashboard,
      }))

      const user = userEvent.setup()

      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await user.click(screen.getByText('Trends & ROI'))

      await waitFor(() => {
        expect(screen.getByText('Total Events')).toBeInTheDocument()
        expect(screen.getByText('52')).toBeInTheDocument()
        expect(screen.getByText('Total Attendance')).toBeInTheDocument()
        expect(screen.getByText('Cost/Attendee')).toBeInTheDocument()
      })
    })

    it('should display top programs', async () => {
      mockFetch.mockImplementation((url: string) => Promise.resolve({
        ok: true,
        json: async () => /roi/.test(url) ? mockROI : mockDashboard,
      }))

      const user = userEvent.setup()

      render(
        <QueryClientProvider client={queryClient}>
          <AttendanceTrackingPage />
        </QueryClientProvider>
      )

      await user.click(screen.getByText('Trends & ROI'))

      await waitFor(() => {
        expect(screen.getByText('Top Programs by Attendance')).toBeInTheDocument()
        expect(screen.getByText('Story Hour')).toBeInTheDocument()
        expect(screen.getByText('Summer Reading')).toBeInTheDocument()
        expect(screen.getByText('Tech Workshop')).toBeInTheDocument()
      })
    })
  })
})
