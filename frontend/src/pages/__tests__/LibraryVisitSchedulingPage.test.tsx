/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

vi.mock('../../i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'libraryVisitScheduling.failedToLoadSchools': 'Failed to load schools',
        'libraryVisitScheduling.failedToLoadLibraryVisits': 'Failed to load visits',
        'libraryVisitScheduling.pleaseFillInAllRequired': 'Please fill in all required fields',
        'libraryVisitScheduling.visitRequestSubmittedSuccessfully': 'Visit request submitted',
        'libraryVisitScheduling.failedToSubmitVisitRequest': 'Failed to submit',
        'libraryVisitScheduling.failedToCancelRequest': 'Failed to cancel',
        'libraryVisitScheduling.whatWouldYouLikeTo': 'What would you like to do?',
        'placeholder.escalationModal.yourName': 'Your name',
        'placeholder.libraryVisitScheduling.eg3rdGrade': 'e.g. 3rd Grade',
        'placeholder.libraryVisitScheduling.numberOfStudents': 'Number of students',
        'toast.interlibraryLoan.requestCancelled': 'Request cancelled',
      }
      return translations[key] || key
    },
  }),
}))

vi.mock('@sentry/browser', () => ({
  captureException: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/components/ui/ModalBackdrop', () => ({
  ModalBackdrop: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="modal-backdrop">{children}</div>
  ),
}))

vi.mock('@/components/ui/Button', () => ({
  Button: ({ children, onClick, ...rest }: { children: React.ReactNode; onClick?: () => void }) => (
    <button onClick={onClick} {...rest}>
      {children}
    </button>
  ),
}))

vi.mock('@/api/types', () => ({
  API_BASE: '/api/v1',
}))

import LibraryVisitSchedulingPage from '../LibraryVisitSchedulingPage'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('LibraryVisitSchedulingPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the empty state when there are no visits or requests', async () => {
    // Page calls /schools first, then /library-visits/{id} and /library-visits/requests/{id}
    // in parallel once a school is auto-selected.
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString()
      if (url.endsWith('/school-partnerships/schools')) {
        return jsonResponse({ schools: [{ id: '1', name: 'Test School' }] })
      }
      if (url.includes('/library-visits/requests/')) {
        return jsonResponse({ requests: [] })
      }
      if (url.includes('/library-visits/')) {
        return jsonResponse({ visits: [] })
      }
      return jsonResponse({}, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<LibraryVisitSchedulingPage />)

    // Heading is unconditional - confirms render
    expect(await screen.findByText('Library Visit Scheduling')).toBeInTheDocument()

    // Empty-state copy for scheduled visits
    await waitFor(() => {
      expect(
        screen.getByText(/No scheduled visits yet/i),
      ).toBeInTheDocument()
    })

    // The page fetched all three expected endpoints
    const urls = fetchMock.mock.calls.map((c) =>
      typeof c[0] === 'string' ? c[0] : (c[0] as URL).toString(),
    )
    expect(urls.some((u) => u.endsWith('/school-partnerships/schools'))).toBe(true)
    expect(urls.some((u) => u.includes('/library-visits/1'))).toBe(true)
    expect(urls.some((u) => u.includes('/library-visits/requests/1'))).toBe(true)
  })

  it('opens the Request Visit modal when the user clicks the trigger', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input.toString()
      if (url.endsWith('/school-partnerships/schools')) {
        return jsonResponse({ schools: [{ id: '1', name: 'Test School' }] })
      }
      if (url.includes('/library-visits/requests/')) {
        return jsonResponse({ requests: [] })
      }
      return jsonResponse({ visits: [] })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<LibraryVisitSchedulingPage />)

    // Wait for initial load to settle
    await waitFor(() => {
      expect(screen.getByText(/No scheduled visits yet/i)).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /request visit/i }))

    // ModalBackdrop renders with the modal heading
    expect(await screen.findByTestId('modal-backdrop')).toBeInTheDocument()
    expect(screen.getByText('Request Library Visit')).toBeInTheDocument()
  })
})
