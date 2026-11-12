/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback ?? key,
  }),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

const mockUseAuth = vi.fn()
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children, actions }: { children: React.ReactNode; actions?: React.ReactNode }) => (
    <div data-testid="admin-shell">{actions}{children}</div>
  ),
}))

const mockGetEvent = vi.fn()
const mockGetRegistrations = vi.fn()
const mockAcknowledge = vi.fn()
const mockAdminCancel = vi.fn()
const mockMarkNoShow = vi.fn()
const mockMarkAttended = vi.fn()
vi.mock('@/api/events-api', () => ({
  getEvent: (...args: unknown[]) => mockGetEvent(...args),
  getEventRegistrations: (...args: unknown[]) => mockGetRegistrations(...args),
  acknowledgeAccommodation: (...args: unknown[]) => mockAcknowledge(...args),
  adminCancelRegistration: (...args: unknown[]) => mockAdminCancel(...args),
  markRegistrationNoShow: (...args: unknown[]) => mockMarkNoShow(...args),
  markRegistrationAttended: (...args: unknown[]) => mockMarkAttended(...args),
}))

const mockListSessions = vi.fn()
const mockCreateSession = vi.fn()
const mockCheckInWalkIn = vi.fn()
vi.mock('@/api/domains/services/attendance-api', () => ({
  listAttendanceSessions: (...args: unknown[]) => mockListSessions(...args),
  createAttendanceSession: (...args: unknown[]) => mockCreateSession(...args),
  checkInWalkIn: (...args: unknown[]) => mockCheckInWalkIn(...args),
}))

// Import after mocks
import EventRosterPage from '../EventRosterPage'

const STAFF_USER = { id: 1, role: 'staff', email: 's@l.org' }

function renderPage(eventId = '42') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/staff/events/${eventId}/roster`]}>
        <Routes>
          <Route path="/staff/events/:eventId/roster" element={<EventRosterPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

const SAMPLE_EVENT = {
  id: 42,
  title: 'Book Club',
  start_time: '2099-01-15T18:00:00Z',
  end_time: '2099-01-15T19:00:00Z',
  location: 'Branch A',
  max_attendees: 20,
  registration_required: true,
  registration_count: 2,
  spots_remaining: 18,
}

const REG_PLAIN = {
  id: 1,
  event_id: 42,
  patron_name: 'Ada Lovelace',
  patron_email: 'ada@l.org',
  patron_phone: null,
  registered_at: '2099-01-01T00:00:00Z',
  status: 'confirmed',
  reminder_requested: false,
  waitlist_position: null,
  accommodation_requested: false,
}

const REG_ACCOMM = {
  ...REG_PLAIN,
  id: 2,
  patron_name: 'Grace Hopper',
  patron_email: 'grace@l.org',
  accommodation_requested: true,
  accommodation_details: 'Wheelchair access',
}

describe('EventRosterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({ user: STAFF_USER, token: 'tok' })
    mockGetEvent.mockResolvedValue(SAMPLE_EVENT)
    mockGetRegistrations.mockResolvedValue({
      registrations: [REG_PLAIN, REG_ACCOMM],
      total: 2,
      waitlist_count: 0,
      spots_remaining: 18,
    })
  })

  it('renders registrant table with mock data', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeInTheDocument()
      expect(screen.getByText('Grace Hopper')).toBeInTheDocument()
    })
    expect(screen.getByText('Book Club')).toBeInTheDocument()
  })

  it('shows Acknowledge button only for accommodation_requested && !acknowledged, and POSTs on click', async () => {
    mockAcknowledge.mockResolvedValue(undefined)
    renderPage()
    await waitFor(() => screen.getByText('Grace Hopper'))

    // Ada has no accommodation request → no button
    const ackButtons = screen.getAllByText('Acknowledge')
    expect(ackButtons).toHaveLength(1)

    fireEvent.click(ackButtons[0]!)
    await waitFor(() => {
      expect(mockAcknowledge).toHaveBeenCalledWith('tok', 42, 2)
    })
  })

  it('hides Acknowledge button on initial render when accommodation_acknowledged_at is set (no session Set involvement)', async () => {
    // Server returns a row that has already been acknowledged in a prior
    // session. The bug we're pinning: pre-fix, the page tracked acks in a
    // session-local Set, so a hard refresh re-showed the button.
    mockGetRegistrations.mockResolvedValue({
      registrations: [
        {
          ...REG_ACCOMM,
          accommodation_acknowledged_at: '2026-05-15T12:00:00Z',
          accommodation_acknowledged_by: 99,
        },
      ],
      total: 1,
      waitlist_count: 0,
      spots_remaining: 19,
    })
    renderPage()
    await waitFor(() => screen.getByText('Grace Hopper'))

    // No Acknowledge button anywhere — API field is source of truth.
    expect(screen.queryByText('Acknowledge')).not.toBeInTheDocument()
    // And the "Acknowledged" pill is shown instead.
    expect(screen.getByText('Acknowledged')).toBeInTheDocument()
  })

  it('mark attended for selected pre-registered patrons uses pre_registered check-in path (registration_id passed)', async () => {
    // The bug we're pinning: before this change, "Mark attended" POSTed a
    // walk-in check-in (check_in_method='walk_in', no registration link)
    // so attribution was muddier than it should be. Now it must hit the
    // new POST /events/{id}/registrations/{rid}/check-in endpoint, which
    // creates a check_in_method='pre_registered' row with registration_id
    // set.
    mockMarkAttended.mockResolvedValue({
      id: 100,
      session_id: 7,
      registration_id: 1,
      check_in_method: 'pre_registered',
      checked_in_at: '2099-01-15T18:00:00Z',
    })

    renderPage()
    await waitFor(() => screen.getByText('Ada Lovelace'))

    const onlyRow = screen
      .getAllByRole('checkbox')
      .filter(
        (cb) =>
          (cb.getAttribute('aria-label') || '').startsWith('Select ') &&
          cb.getAttribute('aria-label') !== 'Select all'
      )
    expect(onlyRow.length).toBe(2)
    fireEvent.click(onlyRow[0]!)
    fireEvent.click(onlyRow[1]!)

    fireEvent.click(screen.getByText(/Mark selected attended/i))

    await waitFor(() => {
      expect(mockMarkAttended).toHaveBeenCalledTimes(2)
    })
    // Each call carries (token, eventId, registrationId) — registrationId
    // is the attribution link that the backend writes onto the
    // AttendanceCheckIn.
    expect(mockMarkAttended).toHaveBeenCalledWith('tok', 42, 1)
    expect(mockMarkAttended).toHaveBeenCalledWith('tok', 42, 2)

    // Critically, the walk-in path is NOT used for pre-registered rows;
    // walk_in remains reserved for the "Add walk-in" form below.
    expect(mockCheckInWalkIn).not.toHaveBeenCalled()
  })

  it('Add walk-in form still uses checkInWalkIn (walk_in path untouched)', async () => {
    mockListSessions.mockResolvedValue({
      data: [{ id: 7, event_id: 42 }],
      pagination: {
        page: 1,
        per_page: 50,
        total: 1,
        total_pages: 1,
        has_next: false,
        has_previous: false,
      },
    })
    mockCheckInWalkIn.mockResolvedValue({ id: 200 })

    renderPage()
    await waitFor(() => screen.getByText('Ada Lovelace'))

    // The small "Add walk-in" form for unregistered patrons.
    const nameInput = screen.getByLabelText(/Name/i)
    fireEvent.change(nameInput, { target: { value: 'Walk-In Patron' } })
    fireEvent.click(screen.getByRole('button', { name: /^Add$/ }))

    await waitFor(() => {
      expect(mockCheckInWalkIn).toHaveBeenCalledTimes(1)
    })
    expect(mockCheckInWalkIn).toHaveBeenCalledWith(
      expect.objectContaining({ session_id: 7, guest_name: 'Walk-In Patron' })
    )
    // And no pre_registered path for the walk-in form.
    expect(mockMarkAttended).not.toHaveBeenCalled()
  })

  it('Print roster triggers window.print', async () => {
    const printSpy = vi.fn()
    // jsdom does not implement window.print; assign before spying.
    Object.defineProperty(window, 'print', { value: printSpy, configurable: true, writable: true })
    renderPage()
    await waitFor(() => screen.getByText('Book Club'))
    fireEvent.click(screen.getByText('Print roster'))
    expect(printSpy).toHaveBeenCalled()
  })

  it('renders empty state when there are no registrations', async () => {
    mockGetRegistrations.mockResolvedValue({
      registrations: [],
      total: 0,
      waitlist_count: 0,
      spots_remaining: 20,
    })
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('No one has signed up yet.')).toBeInTheDocument()
    })
  })

  it('redirects non-staff user with a flash', () => {
    mockUseAuth.mockReturnValue({ user: { id: 9, role: 'patron' }, token: 'tok' })
    renderPage()
    expect(screen.getByText('Staff access required to view event rosters.')).toBeInTheDocument()
    // The 'Go home' button calls navigate('/')
    fireEvent.click(screen.getByText('Go home'))
    expect(mockNavigate).toHaveBeenCalledWith('/')
  })

  it('bulk-select + Mark selected no-show calls markRegistrationNoShow for each, invalidates query, shows toast', async () => {
    const toastModule = await import('react-hot-toast')
    const toast = toastModule.default as unknown as { success: ReturnType<typeof vi.fn>; error: ReturnType<typeof vi.fn> }
    mockMarkNoShow.mockResolvedValue({ id: 1, status: 'no_show' })

    renderPage()
    await waitFor(() => screen.getByText('Ada Lovelace'))

    const onlyRow = screen
      .getAllByRole('checkbox')
      .filter(
        (cb) =>
          (cb.getAttribute('aria-label') || '').startsWith('Select ') &&
          cb.getAttribute('aria-label') !== 'Select all'
      )
    expect(onlyRow.length).toBe(2)
    fireEvent.click(onlyRow[0]!)
    fireEvent.click(onlyRow[1]!)

    fireEvent.click(screen.getByText(/Mark selected no-show/i))

    await waitFor(() => {
      expect(mockMarkNoShow).toHaveBeenCalledTimes(2)
    })
    expect(mockMarkNoShow).toHaveBeenCalledWith('tok', 42, 1)
    expect(mockMarkNoShow).toHaveBeenCalledWith('tok', 42, 2)

    // Roster query gets invalidated → refetch fires.
    await waitFor(() => {
      // First fetch on mount, plus the refetch after invalidate.
      expect(mockGetRegistrations).toHaveBeenCalledTimes(2)
    })

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith(
        expect.stringMatching(/Marked 2 no-show/)
      )
    })
  })

  it('Mark no-show button is disabled when nothing selected, enabled when selection exists', async () => {
    renderPage()
    await waitFor(() => screen.getByText('Ada Lovelace'))

    const button = screen.getByRole('button', { name: /Mark selected no-show/i })
    expect(button).toBeDisabled()

    const firstRowCheckbox = screen
      .getAllByRole('checkbox')
      .find(
        (cb) =>
          (cb.getAttribute('aria-label') || '').startsWith('Select ') &&
          cb.getAttribute('aria-label') !== 'Select all'
      )!
    fireEvent.click(firstRowCheckbox)

    expect(button).not.toBeDisabled()
  })

  it('shows error toast when markRegistrationNoShow rejects', async () => {
    const toastModule = await import('react-hot-toast')
    const toast = toastModule.default as unknown as { success: ReturnType<typeof vi.fn>; error: ReturnType<typeof vi.fn> }
    mockMarkNoShow.mockRejectedValue(new Error('Network exploded'))

    renderPage()
    await waitFor(() => screen.getByText('Ada Lovelace'))

    const firstRowCheckbox = screen
      .getAllByRole('checkbox')
      .find(
        (cb) =>
          (cb.getAttribute('aria-label') || '').startsWith('Select ') &&
          cb.getAttribute('aria-label') !== 'Select all'
      )!
    fireEvent.click(firstRowCheckbox)
    fireEvent.click(screen.getByText(/Mark selected no-show/i))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Network exploded')
    })
  })
})
