/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback ?? key,
  }),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/hooks/usePageTitle', () => ({
  usePageTitle: () => undefined,
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

const submitApplicationMock = vi.fn()
const submitApplicationForReviewMock = vi.fn()
vi.mock('@/api/domains/admin/volunteer-api', () => ({
  volunteerApi: {
    submitApplication: (...args: unknown[]) => submitApplicationMock(...args),
    submitApplicationForReview: (...args: unknown[]) => submitApplicationForReviewMock(...args),
  },
}))

// Import after mocks
import VolunteerApplyPage from '../VolunteerApplyPage'

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <VolunteerApplyPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

beforeEach(() => {
  mockNavigate.mockReset()
  submitApplicationMock.mockReset()
  submitApplicationForReviewMock.mockReset()
  mockUseAuth.mockReturnValue({
    user: { id: 1, first_name: 'Ada', last_name: 'Lovelace', email: 'ada@example.org' },
  })
})

describe('VolunteerApplyPage', () => {
  it('renders the application form with required fields and prefilled user info', () => {
    renderPage()
    expect(screen.getByRole('heading', { name: /volunteer with the library/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/first name/i)).toHaveValue('Ada')
    expect(screen.getByLabelText(/last name/i)).toHaveValue('Lovelace')
    expect(screen.getByLabelText(/email/i)).toHaveValue('ada@example.org')
    expect(screen.getByRole('button', { name: /submit application/i })).toBeInTheDocument()
  })

  it('submits the application end-to-end and navigates back to account on success', async () => {
    submitApplicationMock.mockResolvedValue({ id: 42, status: 'draft' })
    submitApplicationForReviewMock.mockResolvedValue({ id: 42, status: 'submitted' })

    renderPage()

    fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: '555-0100' } })
    fireEvent.click(screen.getByText('Shelving & Sorting'))
    fireEvent.change(screen.getByLabelText(/why do you want to volunteer/i), {
      target: { value: 'I love books and people' },
    })
    fireEvent.click(screen.getByLabelText(/i consent to a background check/i))

    fireEvent.click(screen.getByRole('button', { name: /submit application/i }))

    await waitFor(() => expect(submitApplicationMock).toHaveBeenCalledTimes(1))
    const payload = submitApplicationMock.mock.calls[0]?.[0]
    expect(payload).toMatchObject({
      first_name: 'Ada',
      last_name: 'Lovelace',
      email: 'ada@example.org',
      phone: '555-0100',
      why_volunteer: 'I love books and people',
      background_check_consent: true,
      interests: ['Shelving & Sorting'],
    })

    await waitFor(() => expect(submitApplicationForReviewMock).toHaveBeenCalledWith(42))
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/account?tab=volunteer'))
  })

  it('shows an error toast and does not navigate when the API rejects', async () => {
    const toast = (await import('react-hot-toast')).default
    submitApplicationMock.mockRejectedValue(new Error('Server unavailable'))

    renderPage()

    fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: '555-0100' } })
    fireEvent.click(screen.getByText('Event Support'))
    fireEvent.change(screen.getByLabelText(/why do you want to volunteer/i), {
      target: { value: 'Want to help' },
    })
    fireEvent.click(screen.getByLabelText(/i consent to a background check/i))

    fireEvent.click(screen.getByRole('button', { name: /submit application/i }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Server unavailable'))
    expect(submitApplicationForReviewMock).not.toHaveBeenCalled()
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('does not call the API when required consent or interests are missing', () => {
    renderPage()
    fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: '555-0100' } })
    fireEvent.change(screen.getByLabelText(/why do you want to volunteer/i), {
      target: { value: 'I want to help' },
    })
    // No interests selected, no consent given.
    fireEvent.click(screen.getByRole('button', { name: /submit application/i }))
    expect(submitApplicationMock).not.toHaveBeenCalled()
  })
})
