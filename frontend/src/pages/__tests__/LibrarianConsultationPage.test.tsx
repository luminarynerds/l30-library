/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { getTranslation } from '../../i18n/translations'

// i18n mock: resolve through the real en dictionary (setup.ts preloads it) so
// params-form t(key, {vars}) interpolates like production; the page renders
// without an I18nProvider here, so the hook itself must be mocked.
vi.mock('../../i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, paramsOrFallback?: Record<string, unknown> | string) =>
      typeof paramsOrFallback === 'string'
        ? getTranslation(key, 'en', undefined, paramsOrFallback)
        : getTranslation(key, 'en', paramsOrFallback),
  }),
}))

const toastSuccess = vi.fn()
const toastError = vi.fn()
vi.mock('react-hot-toast', () => ({
  default: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

vi.mock('@/components/ui/ModalBackdrop', () => ({
  ModalBackdrop: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="modal-backdrop">{children}</div>
  ),
}))

const mockFetchApi = vi.fn()
vi.mock('@/api/fetchApi', () => ({
  fetchApi: (path: string, init?: RequestInit) => mockFetchApi(path, init),
}))

// Import after mocks
import LibrarianConsultationPage from '../LibrarianConsultationPage'

const SCHOOL = {
  id: 1,
  name: 'Maple Elementary',
  address: '1 Maple Ln',
  city: 'Springfield',
  state: 'OH',
  partnership_tier: 'gold',
}

// Use TODAY so the filtered-by-selectedDate slot list renders the seeded slot
// (selectedDate defaults to new Date()).
const TODAY_ISO = new Date().toISOString().split('T')[0] as string

const SLOT_A = {
  id: 101,
  title: 'Curriculum Alignment Chat',
  librarian_id: 5,
  description: 'Discuss curriculum integration',
  consultation_type: 'curriculum',
  scheduled_date: TODAY_ISO,
  start_time: '10:00',
  end_time: '10:30',
  duration_minutes: 30,
  current_participants: 0,
  max_participants: 1,
}

describe('LibrarianConsultationPage', () => {
  beforeEach(() => {
    mockFetchApi.mockReset()
    toastSuccess.mockReset()
    toastError.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the header on initial load', () => {
    mockFetchApi.mockImplementation(() => new Promise(() => {}))

    render(<LibrarianConsultationPage />)

    expect(screen.getByText('Librarian Consultations')).toBeInTheDocument()
  })

  it('shows the empty-state when no slots exist for the selected date', async () => {
    mockFetchApi.mockImplementation((path: string) => {
      if (path === '/auth/me') return Promise.resolve({ id: 1 })
      if (path === '/school-partnerships/schools') return Promise.resolve([SCHOOL])
      if (path.endsWith('/my-registrations')) {
        return Promise.resolve({ registrations: [] })
      }
      if (path.includes('/consultation-slots/')) return Promise.resolve([])
      return Promise.resolve({})
    })

    render(<LibrarianConsultationPage />)

    // Wait for the school selector card to render
    await waitFor(() => {
      expect(screen.getByText('Maple Elementary')).toBeInTheDocument()
    })

    // Empty-state copy in the slots grid
    await waitFor(() => {
      expect(
        screen.getByText(/No available consultations/i),
      ).toBeInTheDocument()
    })
  })

  it('surfaces a toast when /schools rejects', async () => {
    mockFetchApi.mockImplementation((path: string) => {
      if (path === '/auth/me') return Promise.resolve({ id: 1 })
      if (path === '/school-partnerships/schools') {
        return Promise.reject(new Error('boom'))
      }
      return Promise.resolve({})
    })

    render(<LibrarianConsultationPage />)

    await waitFor(() => {
      expect(toastError).toHaveBeenCalled()
    })
    expect(
      toastError.mock.calls.some((c) =>
        String(c[0]).includes('Failed to load schools'),
      ),
    ).toBe(true)
  })

  it('renders an available slot and its key labels', async () => {
    mockFetchApi.mockImplementation((path: string) => {
      if (path === '/auth/me') return Promise.resolve({ id: 1 })
      if (path === '/school-partnerships/schools') return Promise.resolve([SCHOOL])
      if (path.endsWith('/my-registrations')) {
        return Promise.resolve({ registrations: [] })
      }
      if (path.includes('/consultation-slots/')) return Promise.resolve([SLOT_A])
      return Promise.resolve({})
    })

    render(<LibrarianConsultationPage />)

    // Slot title and consultation type render on the card
    await waitFor(() => {
      expect(screen.getByText('Curriculum Alignment Chat')).toBeInTheDocument()
    })
    // "curriculum" appears both on the SlotCard type chip AND in the sidebar
    // filter list (derived from consultationTypes); assert at least one match.
    expect(screen.getAllByText('curriculum').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/30 min/)).toBeInTheDocument()
  })

  it('opens the booking modal and POSTs to /register on confirm', async () => {
    mockFetchApi.mockImplementation((path: string, init?: RequestInit) => {
      if (path === '/auth/me') return Promise.resolve({ id: 1 })
      if (path === '/school-partnerships/schools') return Promise.resolve([SCHOOL])
      if (path.endsWith('/my-registrations')) {
        return Promise.resolve({ registrations: [] })
      }
      if (path.endsWith(`/${SLOT_A.id}/register`) && init?.method === 'POST') {
        return Promise.resolve({ ok: true })
      }
      if (path.includes('/consultation-slots/')) return Promise.resolve([SLOT_A])
      return Promise.resolve({})
    })

    render(<LibrarianConsultationPage />)

    // Wait for the slot card to render
    await waitFor(() => {
      expect(screen.getByText('Curriculum Alignment Chat')).toBeInTheDocument()
    })

    // Click the "Book Consultation" button on the card
    fireEvent.click(screen.getByRole('button', { name: /Book Consultation/i }))

    // Modal opens (mocked ModalBackdrop renders the children) with "Confirm Booking"
    await waitFor(() => {
      expect(screen.getByTestId('modal-backdrop')).toBeInTheDocument()
    })
    // "Confirm Booking" appears as both the modal title and the confirm button label.
    expect(screen.getAllByText(/Confirm Booking/i).length).toBeGreaterThan(0)

    // Click the confirm button inside the modal
    fireEvent.click(screen.getByRole('button', { name: /^Confirm Booking$/i }))

    // The POST register call was issued and success toast fired
    await waitFor(() => {
      const calls = mockFetchApi.mock.calls
      expect(
        calls.some(
          (c) =>
            String(c[0]).endsWith(`/${SLOT_A.id}/register`) &&
            (c[1] as RequestInit | undefined)?.method === 'POST',
        ),
      ).toBe(true)
    })
    await waitFor(() => {
      expect(toastSuccess).toHaveBeenCalled()
    })
  })
})
