/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * RoomBookingPage Edge Case Tests
 *
 * Tests boundary conditions and error handling:
 * - Empty rooms list
 * - Guest count exceeding capacity
 * - Form validation (missing required fields)
 * - HTTP error handling (409 conflict, 401 unauthorized, network failures)
 * - Double-submit prevention
 * - Slot selection and reset behavior
 * - Success screen states (confirmed vs pending approval)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent, within } from '../utils/test-utils'
import userEvent from '@testing-library/user-event'
import RoomBookingPage from '@/pages/RoomBookingPage'
import { API_BASE } from '@/api/types'

// Mock i18n — the component uses t() without destructuring from useTranslation.
// The real t() (src/i18n/I18nContext.tsx) accepts either a string fallback or a
// params object for `{placeholder}`-style interpolation — mirror both here since
// RoomBookingPage/RoomBookingForm use both forms.
const tFn = (key: string, paramsOrFallback?: Record<string, unknown> | string) => {
  const translations: Record<string, string> = {
    'roomBooking.pleaseFillInAllRequired': 'Please fill in all required fields',
    'roomBooking.roomReservationSubmittedForApproval': 'Room reservation submitted for approval!',
    'roomBooking.thisTimeSlotIsNo': 'This time slot is no longer available. Please select another.',
    'roomBooking.pleaseLogInToMake': 'Please log in to make a reservation',
    'roomBooking.yourRoomReservationHasBeen': 'Your room reservation has been confirmed! You will receive a confirmation email at',
    'roomBooking.noRoomsAvailableAtThis': 'No rooms available at this time',
    'roomBooking.pleaseCheckBackLaterOr': 'Please check back later or contact the front desk.',
    'roomBooking.noAvailableTimeSlotsFor': 'No available time slots for this date.',
    'roomBooking.trySelectingADifferentDate': 'Try selecting a different date or room.',
    'placeholder.roomBooking.johnDoe': 'John Doe',
    'placeholder.roomBooking.egStudyGroupTeam': 'e.g. Study group, Team meeting, Presentation practice',
    'placeholder.registrationModal.johnexamplecom': 'john@example.com',
    'placeholder.guestPassForm.5551234567': '(555) 123-4567',
    'toast.roomBooking.guestCountExceedsRoomCapacity': 'Guest count exceeds room capacity of {capacity}',
    'toast.roomBooking.roomReservationConfirmed': 'Room reservation confirmed!',
    'toast.roomBooking.failedToSubmitReservation': 'Failed to submit reservation',
    'toast.roomBooking.checkedInSuccessfully': 'Checked in successfully!',
    'toast.computers.reservationCancelled': 'Reservation cancelled',
  }
  const template = translations[key]
  if (template === undefined) {
    return typeof paramsOrFallback === 'string' ? paramsOrFallback : key
  }
  if (typeof paramsOrFallback === 'string' || paramsOrFallback === undefined) return template
  return template.replace(/\{(\w+)\}/g, (_match, name) => String(paramsOrFallback[name] ?? `{${name}}`))
}
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: tFn, language: 'en', setLanguage: vi.fn(), isRTL: false }),
}))
// Mock react-hot-toast
const mockToastError = vi.fn()
const mockToastSuccess = vi.fn()
vi.mock('react-hot-toast', () => ({
  default: {
    error: (...args: unknown[]) => mockToastError(...args),
    success: (...args: unknown[]) => mockToastSuccess(...args),
  },
}))

// Mock API client
const mockGet = vi.fn()
const mockPost = vi.fn()
vi.mock('@/lib/api-client', () => {
  // friendlyErrorMessage (src/utils/friendlyError.ts) does `error instanceof ApiError`
  // against the real class, so the mock must export a matching ApiError -- otherwise
  // that check throws (ReferenceError: ApiError is not defined on the mock) whenever
  // a rejection reaches it, e.g. the availability-fetch error path. Declared inside
  // the factory since vi.mock factories are hoisted above top-level module code.
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.name = 'ApiError'
      this.status = status
    }
  }
  return {
    default: {
      get: (...args: unknown[]) => mockGet(...args),
      post: (...args: unknown[]) => mockPost(...args),
    },
    api: {
      get: (...args: unknown[]) => mockGet(...args),
      post: (...args: unknown[]) => mockPost(...args),
    },
    // BrandingContext (pulled in by the shared test-utils AllProviders wrapper)
    // calls fetchApi directly for setup-status; it fails soft on rejection.
    fetchApi: vi.fn().mockRejectedValue(new Error('not mocked in this test')),
    ApiError,
  }
})

// Sample room data
const STUDY_ROOM = {
  id: 1,
  name: 'Study Room A',
  description: 'A quiet study room',
  branch_name: null,
  room_type: 'study_room',
  capacity: 4,
  floor: '1st Floor',
  room_number: '101',
  amenities: ['WiFi', 'Power Outlets'],
  requires_approval: false,
  max_duration_minutes: 120,
  min_duration_minutes: 30,
  advance_booking_days: 14,
  image_url: null,
  is_active: true,
}

const MEETING_ROOM = {
  id: 2,
  name: 'Meeting Room B',
  description: 'A large meeting room',
  branch_name: null,
  room_type: 'meeting_room',
  capacity: 12,
  floor: '2nd Floor',
  room_number: '201',
  amenities: ['WiFi', 'Projector', 'Whiteboard'],
  requires_approval: true,
  max_duration_minutes: 240,
  min_duration_minutes: 60,
  advance_booking_days: 30,
  image_url: null,
  is_active: true,
}

const MOCK_ROOMS_RESPONSE = {
  items: [STUDY_ROOM, MEETING_ROOM],
  total: 2,
  page: 1,
  per_page: 20,
}

const MOCK_AVAILABILITY = {
  room_id: 1,
  room_name: 'Study Room A',
  date: '2026-03-15',
  available_slots: [
    {
      start_time: '2026-03-15T10:00:00Z',
      end_time: '2026-03-15T11:00:00Z',
      duration_minutes: 60,
    },
    {
      start_time: '2026-03-15T14:00:00Z',
      end_time: '2026-03-15T15:00:00Z',
      duration_minutes: 60,
    },
  ],
  reservations: [],
}

const MOCK_EMPTY_AVAILABILITY = {
  room_id: 1,
  room_name: 'Study Room A',
  date: '2026-03-15',
  available_slots: [],
  reservations: [
    { id: 99, start_time: '2026-03-15T09:00:00Z', end_time: '2026-03-15T21:00:00Z', status: 'confirmed' },
  ],
}

// Helper: find the date input (type="date")
function getDateInput(): HTMLInputElement {
  return document.querySelector('input[type="date"]') as HTMLInputElement
}

// Helper: find the guest count input (type="number")
function getGuestInput(): HTMLInputElement {
  return document.querySelector('input[type="number"]') as HTMLInputElement
}

// Helper: get the room radio by value
function getRoomRadio(roomId: number): HTMLInputElement {
  return document.querySelector(`input[type="radio"][value="${roomId}"]`) as HTMLInputElement
}

// Helper: get the available start-time slot buttons (time-first flow: pick a
// start time, e.g. "10:00 AM" — duration defaults to the room's minimum and a
// separate duration picker appears once a start time is chosen).
function getSlotButtons(): HTMLElement[] {
  const group = screen.getByRole('group', { name: /available time slots/i })
  return within(group).getAllByRole('button')
}

// Helper: select a room and set a date, then wait for slots
async function selectRoomAndDate(
  user: ReturnType<typeof userEvent.setup>,
  roomId: number,
  date: string,
) {
  await user.click(getRoomRadio(roomId))
  fireEvent.change(getDateInput(), { target: { value: date } })
}

describe('RoomBookingPage Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default: rooms load successfully
    mockGet.mockImplementation((url: string) => {
      if (url.startsWith(`${API_BASE}/rooms?`)) return Promise.resolve(MOCK_ROOMS_RESPONSE)
      if (url.includes('/availability')) return Promise.resolve(MOCK_AVAILABILITY)
      return Promise.resolve({})
    })
  })

  // ================================================================
  // Empty / loading states
  // ================================================================

  describe('Empty and Error States', () => {
    it('shows "no rooms available" when API returns empty list', async () => {
      mockGet.mockImplementation((url: string) => {
        if (url.startsWith(`${API_BASE}/rooms?`)) {
          return Promise.resolve({ items: [], total: 0, page: 1, per_page: 20 })
        }
        return Promise.resolve({})
      })

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('No rooms available at this time')).toBeInTheDocument()
      })
    })

    it('shows error message when rooms API fails', async () => {
      mockGet.mockImplementation((url: string) => {
        if (url.startsWith(`${API_BASE}/rooms?`)) {
          // useRoomBookings only trusts `.message` off a real Error instance
          // (`err instanceof Error ? err.message : 'Failed to load rooms'`);
          // a plain object here falls through to the generic fallback text.
          return Promise.reject(new Error('Server error'))
        }
        return Promise.resolve({})
      })

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Server error')).toBeInTheDocument()
      })
    })

    it('shows loading spinner while rooms are being fetched', () => {
      mockGet.mockReturnValue(new Promise(() => {}))

      render(<RoomBookingPage />)

      expect(screen.getByText('Loading available rooms...')).toBeInTheDocument()
    })
  })

  // ================================================================
  // Room selection and date interaction
  // ================================================================

  describe('Room and Date Interaction', () => {
    it('enables the date input up front (time-first flow: date before room)', async () => {
      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      // Current UX is time-first: pick a date, then room cards show that
      // date's availability. The date input is never gated on a room pick.
      expect(getDateInput()).not.toBeDisabled()
    })

    it('shows a "Staff approves" cost/approval summary for meeting rooms', async () => {
      render(<RoomBookingPage />)

      // The old standalone "Requires approval" badge was replaced by a combined
      // cost + approval-turnaround line (costApprovalSummary in RoomBookingForm).
      await waitFor(() => {
        expect(screen.getByText(/Staff approves within 1 business day/)).toBeInTheDocument()
      })
    })

    it('shows approval notice when a room requiring approval is selected', async () => {
      const user = userEvent.setup()

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Meeting Room B')).toBeInTheDocument()
      })

      await user.click(getRoomRadio(2))

      expect(screen.getByText(/Approval Required/)).toBeInTheDocument()
    })
  })

  // ================================================================
  // Availability edge cases
  // ================================================================

  describe('Availability Edge Cases', () => {
    it('shows "no available time slots" when day is fully booked', async () => {
      const user = userEvent.setup()

      mockGet.mockImplementation((url: string) => {
        if (url.startsWith(`${API_BASE}/rooms?`)) return Promise.resolve(MOCK_ROOMS_RESPONSE)
        if (url.includes('/availability')) return Promise.resolve(MOCK_EMPTY_AVAILABILITY)
        return Promise.resolve({})
      })

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      await selectRoomAndDate(user, 1, '2026-03-15')

      await waitFor(() => {
        expect(screen.getByText('No available time slots for this date.')).toBeInTheDocument()
      })
    })

    it('shows toast error when availability API fails', async () => {
      const user = userEvent.setup()

      mockGet.mockImplementation((url: string) => {
        if (url.startsWith(`${API_BASE}/rooms?`)) return Promise.resolve(MOCK_ROOMS_RESPONSE)
        // RoomBookingPage's loadAvailability() runs every rejection through
        // friendlyErrorMessage(), which keyword-matches real Error messages into
        // a small set of user-facing strings rather than surfacing them verbatim.
        // "service unavailable" hits its 5xx bucket, so that's what the toast gets.
        if (url.includes('/availability')) return Promise.reject(new Error('Availability service unavailable'))
        return Promise.resolve({})
      })

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      await selectRoomAndDate(user, 1, '2026-03-15')

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith('Something went wrong on our end. Please try again in a moment.')
      })
    })

    it('clears selected slot when room changes', async () => {
      const user = userEvent.setup()

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      // Select study room and date
      await selectRoomAndDate(user, 1, '2026-03-15')

      // Wait for slots to appear
      await waitFor(() => {
        expect(getSlotButtons().length).toBeGreaterThan(0)
      })

      // Switch to meeting room - should clear availability/slot
      await user.click(getRoomRadio(2))

      // Submit button should still be disabled (no slot selected)
      const submitButton = screen.getByRole('button', { name: /submit for approval/i })
      expect(submitButton).toBeDisabled()
    })
  })

  // ================================================================
  // Guest count validation
  // ================================================================

  describe('Guest Count Validation', () => {
    it('shows capacity warning when guest count exceeds room capacity', async () => {
      const user = userEvent.setup()

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      // Select room (capacity 4)
      await user.click(getRoomRadio(1))

      // Set guest count to 5
      const guestInput = getGuestInput()
      await user.clear(guestInput)
      await user.type(guestInput, '5')

      expect(screen.getByText('Exceeds room capacity of 4')).toBeInTheDocument()
    })

    it('prevents submission when guest count exceeds capacity', async () => {
      const user = userEvent.setup()

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      await selectRoomAndDate(user, 1, '2026-03-15')

      await waitFor(() => {
        expect(getSlotButtons().length).toBeGreaterThan(0)
      })

      // Select a slot
      const slotButtons = getSlotButtons()
      await user.click(slotButtons[0]!)

      // Set guest count above capacity
      const guestInput = getGuestInput()
      await user.clear(guestInput)
      await user.type(guestInput, '10')

      // Fill required fields
      await user.type(screen.getByPlaceholderText('John Doe'), 'Test User')
      await user.type(screen.getByPlaceholderText('john@example.com'), 'test@example.com')

      // Submit via fireEvent to bypass native validation
      const form = document.querySelector('form') as HTMLFormElement
      fireEvent.submit(form)

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith(
          expect.stringContaining('exceeds room capacity')
        )
      })
      expect(mockPost).not.toHaveBeenCalled()
    })
  })

  // ================================================================
  // Form validation edge cases
  // ================================================================

  describe('Form Validation', () => {
    it('shows error toast when submitting without required fields', async () => {
      const user = userEvent.setup()

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      await selectRoomAndDate(user, 1, '2026-03-15')

      await waitFor(() => {
        expect(getSlotButtons().length).toBeGreaterThan(0)
      })

      // Select a slot
      const slotButtons = getSlotButtons()
      await user.click(slotButtons[0]!)

      // Don't fill name/email - submit via fireEvent to bypass native validation
      const form = document.querySelector('form') as HTMLFormElement
      fireEvent.submit(form)

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith('Please fill in all required fields')
      })
      expect(mockPost).not.toHaveBeenCalled()
    })

    it('does not render the submit button until a room is selected', async () => {
      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      // The whole slots/guests/contact/submit section is gated on selectedRoom
      // (RoomBookingForm wraps it in `{selectedRoom && (<>...)}`) — there's no
      // disabled button to find before a room is picked, it simply isn't there.
      expect(screen.queryByRole('button', { name: /reserve room/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /submit for approval/i })).not.toBeInTheDocument()
    })

    it('disables submit button when no time slot is selected', async () => {
      const user = userEvent.setup()

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      await user.click(getRoomRadio(1))

      const submitButton = screen.getByRole('button', { name: /reserve room/i })
      expect(submitButton).toBeDisabled()
    })
  })

  // ================================================================
  // Submission error handling
  // ================================================================

  describe('Submission Error Handling', () => {
    async function fillAndSubmitForm() {
      const user = userEvent.setup()

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      await selectRoomAndDate(user, 1, '2026-03-15')

      await waitFor(() => {
        expect(getSlotButtons().length).toBeGreaterThan(0)
      })

      const slotButtons = getSlotButtons()
      await user.click(slotButtons[0]!)

      await user.type(screen.getByPlaceholderText('John Doe'), 'Test User')
      await user.type(screen.getByPlaceholderText('john@example.com'), 'test@example.com')

      const submitButton = screen.getByRole('button', { name: /reserve room/i })
      await user.click(submitButton)

      return user
    }

    it('handles 409 conflict by refreshing availability', async () => {
      mockPost.mockRejectedValueOnce({ status: 409, message: 'Conflict' })

      const refreshedAvailability = {
        ...MOCK_AVAILABILITY,
        available_slots: [
          {
            start_time: '2026-03-15T16:00:00Z',
            end_time: '2026-03-15T17:00:00Z',
            duration_minutes: 60,
          },
        ],
      }

      mockGet.mockImplementation((url: string) => {
        if (url.startsWith(`${API_BASE}/rooms?`)) return Promise.resolve(MOCK_ROOMS_RESPONSE)
        if (url.includes('/availability')) return Promise.resolve(refreshedAvailability)
        return Promise.resolve({})
      })

      await fillAndSubmitForm()

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith(
          'This time slot is no longer available. Please select another.'
        )
      })
    })

    it('handles 401 unauthorized with login prompt', async () => {
      mockPost.mockRejectedValueOnce({ status: 401, message: 'Unauthorized' })

      await fillAndSubmitForm()

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith('Please log in to make a reservation')
      })
    })

    it('handles generic server error', async () => {
      mockPost.mockRejectedValueOnce({ status: 500, message: 'Internal server error' })

      await fillAndSubmitForm()

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith('Internal server error')
      })
    })

    it('handles network error with fallback message', async () => {
      mockPost.mockRejectedValueOnce({})

      await fillAndSubmitForm()

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith('Failed to submit reservation')
      })
    })
  })

  // ================================================================
  // Success screen edge cases
  // ================================================================

  describe('Success Screen', () => {
    it('shows confirmed status for auto-approved study room', async () => {
      const user = userEvent.setup()
      mockPost.mockResolvedValueOnce({ status: 'confirmed', id: 123 })

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      await selectRoomAndDate(user, 1, '2026-03-15')

      await waitFor(() => {
        expect(getSlotButtons().length).toBeGreaterThan(0)
      })

      const slotButtons = getSlotButtons()
      await user.click(slotButtons[0]!)

      await user.type(screen.getByPlaceholderText('John Doe'), 'Test User')
      await user.type(screen.getByPlaceholderText('john@example.com'), 'test@example.com')

      await user.click(screen.getByRole('button', { name: /reserve room/i }))

      await waitFor(() => {
        expect(screen.getByText('Reservation Confirmed!')).toBeInTheDocument()
      })

      expect(mockToastSuccess).toHaveBeenCalledWith('Room reservation confirmed!')
    })

    it('shows pending status for meeting room requiring approval', async () => {
      const user = userEvent.setup()
      mockPost.mockResolvedValueOnce({ status: 'pending', id: 124 })

      mockGet.mockImplementation((url: string) => {
        if (url.startsWith(`${API_BASE}/rooms?`)) return Promise.resolve(MOCK_ROOMS_RESPONSE)
        if (url.includes('/availability')) {
          return Promise.resolve({
            room_id: 2,
            room_name: 'Meeting Room B',
            date: '2026-03-15',
            available_slots: [
              {
                start_time: '2026-03-15T10:00:00Z',
                end_time: '2026-03-15T12:00:00Z',
                duration_minutes: 120,
              },
            ],
            reservations: [],
          })
        }
        return Promise.resolve({})
      })

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Meeting Room B')).toBeInTheDocument()
      })

      await selectRoomAndDate(user, 2, '2026-03-15')

      await waitFor(() => {
        expect(getSlotButtons().length).toBeGreaterThan(0)
      })

      await user.click(getSlotButtons()[0]!)
      await user.type(screen.getByPlaceholderText('John Doe'), 'Test User')
      await user.type(screen.getByPlaceholderText('john@example.com'), 'test@example.com')

      await user.click(screen.getByRole('button', { name: /submit for approval/i }))

      await waitFor(() => {
        expect(screen.getByText('Reservation Submitted for Approval')).toBeInTheDocument()
      })

      expect(screen.getByText(/requires staff approval/)).toBeInTheDocument()
      expect(mockToastSuccess).toHaveBeenCalledWith('Room reservation submitted for approval!')
    })

    it('resets form when "Book Another Room" is clicked', async () => {
      const user = userEvent.setup()
      mockPost.mockResolvedValueOnce({ status: 'confirmed', id: 125 })

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      await selectRoomAndDate(user, 1, '2026-03-15')

      await waitFor(() => {
        expect(getSlotButtons().length).toBeGreaterThan(0)
      })

      const slotButtons = getSlotButtons()
      await user.click(slotButtons[0]!)
      await user.type(screen.getByPlaceholderText('John Doe'), 'Test User')
      await user.type(screen.getByPlaceholderText('john@example.com'), 'test@example.com')

      await user.click(screen.getByRole('button', { name: /reserve room/i }))

      await waitFor(() => {
        expect(screen.getByText('Reservation Confirmed!')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Book Another Room'))

      // "Book a Room" also matches the tab button text, so disambiguate with
      // the page heading (role=heading) to confirm we're back on the main page.
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'Book a Room' })).toBeInTheDocument()
      })

      // resetForm() clears selectedRoom/selectedDate; with no room selected the
      // whole slots/guests/contact/submit section (gated on selectedRoom) is gone
      // again, and the date input is back to its empty initial value.
      expect(getDateInput().value).toBe('')
      expect(getRoomRadio(1)).not.toBeChecked()
      expect(screen.queryByRole('button', { name: /reserve room/i })).not.toBeInTheDocument()
    })
  })

  // ================================================================
  // Double-submit prevention
  // ================================================================

  describe('Double Submit Prevention', () => {
    it('disables submit button while submission is in progress', async () => {
      const user = userEvent.setup()
      mockPost.mockReturnValue(new Promise(() => {}))

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      await selectRoomAndDate(user, 1, '2026-03-15')

      await waitFor(() => {
        expect(getSlotButtons().length).toBeGreaterThan(0)
      })

      const slotButtons = getSlotButtons()
      await user.click(slotButtons[0]!)

      await user.type(screen.getByPlaceholderText('John Doe'), 'Test User')
      await user.type(screen.getByPlaceholderText('john@example.com'), 'test@example.com')

      await user.click(screen.getByRole('button', { name: /reserve room/i }))

      await waitFor(() => {
        expect(screen.getByText('Submitting...')).toBeInTheDocument()
      })

      const disabledButton = screen.getByRole('button', { name: /submitting/i })
      expect(disabledButton).toBeDisabled()
      expect(mockPost).toHaveBeenCalledTimes(1)
    })
  })

  // ================================================================
  // Amenities display
  // ================================================================

  describe('Amenities Display', () => {
    it('shows amenities when a room with amenities is selected', async () => {
      const user = userEvent.setup()

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      await user.click(getRoomRadio(1))

      await waitFor(() => {
        expect(screen.getByText('Room Amenities')).toBeInTheDocument()
      })
    })
  })

  // ================================================================
  // Submit button text
  // ================================================================

  describe('Submit Button Text', () => {
    it('says "Reserve Room" for auto-approved rooms', async () => {
      const user = userEvent.setup()

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Study Room A')).toBeInTheDocument()
      })

      await selectRoomAndDate(user, 1, '2026-03-15')

      await waitFor(() => {
        expect(getSlotButtons().length).toBeGreaterThan(0)
      })

      const slotButtons = getSlotButtons()
      await user.click(slotButtons[0]!)

      expect(screen.getByRole('button', { name: /reserve room/i })).toBeInTheDocument()
    })

    it('says "Submit for Approval" for rooms requiring approval', async () => {
      const user = userEvent.setup()

      mockGet.mockImplementation((url: string) => {
        if (url.startsWith(`${API_BASE}/rooms?`)) return Promise.resolve(MOCK_ROOMS_RESPONSE)
        if (url.includes('/availability')) {
          return Promise.resolve({
            room_id: 2,
            room_name: 'Meeting Room B',
            date: '2026-03-15',
            available_slots: [
              {
                start_time: '2026-03-15T10:00:00Z',
                end_time: '2026-03-15T12:00:00Z',
                duration_minutes: 120,
              },
            ],
            reservations: [],
          })
        }
        return Promise.resolve({})
      })

      render(<RoomBookingPage />)

      await waitFor(() => {
        expect(screen.getByText('Meeting Room B')).toBeInTheDocument()
      })

      await selectRoomAndDate(user, 2, '2026-03-15')

      await waitFor(() => {
        expect(getSlotButtons().length).toBeGreaterThan(0)
      })

      await user.click(getSlotButtons()[0]!)

      expect(screen.getByRole('button', { name: /submit for approval/i })).toBeInTheDocument()
    })
  })
})