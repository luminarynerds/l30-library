/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import React from 'react'

// i18n mock: interpolate {{name}} placeholders so we can assert against strings.
// Both '@/i18n' (used by the page) and '@/i18n/I18nContext' (used by Button) need stubs.
const tFn = (key: string, vars?: Record<string, unknown>) => {
  if (!vars) return key
  return Object.entries(vars).reduce<string>(
    (acc, [k, v]) => acc.replace(new RegExp(`{{${k}}}`, 'g'), String(v)),
    key,
  )
}
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: tFn }),
}))
vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({ t: tFn }),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

vi.mock('@/components/ui/ModalBackdrop', () => ({
  ModalBackdrop: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="modal-backdrop">{children}</div>
  ),
}))

// StaffLayout pulls in AuthContext + PreferencesContext + a heavy sidebar; stub it.
vi.mock('../StaffLayout', () => ({
  StaffLayout: ({
    children,
    actions,
    title,
  }: {
    children: React.ReactNode
    actions?: React.ReactNode
    title?: string
  }) => (
    <div>
      {title && <h1>{title}</h1>}
      {actions}
      {children}
    </div>
  ),
}))

import StaffLibraryVisitsPage from '../StaffLibraryVisitsPage'

const PENDING_REQUESTS = [
  {
    id: 101,
    school_id: 1,
    school_name: 'Maple Elementary',
    teacher_user_id: 42,
    teacher_name: 'Ms. Carver',
    requested_date: '2026-06-01T15:00:00Z',
    scheduled_date: null,
    number_of_students: 24,
    grade_level: '3rd',
    purpose: 'Storytime + library card signups',
    status: 'pending' as const,
    rejection_reason: null,
    approved_at: null,
    created_at: '2026-05-14T10:00:00Z',
  },
  {
    id: 102,
    school_id: 2,
    school_name: 'Oak High',
    teacher_user_id: 43,
    teacher_name: 'Mr. Diaz',
    requested_date: '2026-06-08T16:30:00Z',
    scheduled_date: null,
    number_of_students: 18,
    grade_level: '9th',
    purpose: 'Research skills workshop',
    status: 'pending' as const,
    rejection_reason: null,
    approved_at: null,
    created_at: '2026-05-14T11:00:00Z',
  },
]

let fetchSpy: ReturnType<typeof vi.spyOn>
const fetchCalls: Array<{ url: string; init?: RequestInit }> = []

function installFetch() {
  fetchCalls.length = 0
  fetchSpy = vi
    .spyOn(global, 'fetch')
    .mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : (input as URL).toString()
      fetchCalls.push({ url, init })
      if (url.endsWith('/school-partnerships/library-visits/requests')) {
        return new Response(JSON.stringify({ requests: PENDING_REQUESTS }), { status: 200 })
      }
      if (
        url.includes('/school-partnerships/library-visits/requests/') &&
        url.endsWith('/approve')
      ) {
        return new Response(JSON.stringify({ id: 101, status: 'scheduled' }), { status: 200 })
      }
      if (
        url.includes('/school-partnerships/library-visits/requests/') &&
        url.endsWith('/reject')
      ) {
        return new Response(JSON.stringify({ id: 102, status: 'rejected' }), { status: 200 })
      }
      return new Response(JSON.stringify({}), { status: 404 })
    })
}

describe('StaffLibraryVisitsPage', () => {
  beforeEach(() => {
    installFetch()
  })
  afterEach(() => {
    fetchSpy.mockRestore()
  })

  it('renders both pending requests in the table', async () => {
    render(<StaffLibraryVisitsPage />)
    await waitFor(() => {
      expect(screen.getByTestId('pending-row-101')).toBeInTheDocument()
      expect(screen.getByTestId('pending-row-102')).toBeInTheDocument()
    })
    expect(screen.getByText('Ms. Carver')).toBeInTheDocument()
    expect(screen.getByText('Mr. Diaz')).toBeInTheDocument()
  })

  it('opens approve modal and posts to the approve endpoint with a scheduledDate', async () => {
    render(<StaffLibraryVisitsPage />)
    await waitFor(() => expect(screen.getByTestId('approve-101')).toBeInTheDocument())

    fireEvent.click(screen.getByTestId('approve-101'))

    const dateInput = await screen.findByTestId('approve-date-input')
    expect(dateInput).toBeInTheDocument()
    fireEvent.change(dateInput, { target: { value: '2026-06-15T14:00' } })

    fireEvent.click(screen.getByTestId('approve-submit'))

    await waitFor(() => {
      const approveCall = fetchCalls.find(
        (c) => c.url.endsWith('/library-visits/requests/101/approve') && c.init?.method === 'POST',
      )
      expect(approveCall).toBeTruthy()
      const body = JSON.parse((approveCall!.init!.body as string) || '{}')
      expect(body.scheduledDate).toMatch(/2026-06-15/)
    })
  })

  it('opens reject modal and posts to the reject endpoint with a reason', async () => {
    render(<StaffLibraryVisitsPage />)
    await waitFor(() => expect(screen.getByTestId('reject-102')).toBeInTheDocument())

    fireEvent.click(screen.getByTestId('reject-102'))

    const reasonInput = await screen.findByTestId('reject-reason-input')
    fireEvent.change(reasonInput, {
      target: { value: 'Library is closed for inventory that week' },
    })

    fireEvent.click(screen.getByTestId('reject-submit'))

    await waitFor(() => {
      const rejectCall = fetchCalls.find(
        (c) => c.url.endsWith('/library-visits/requests/102/reject') && c.init?.method === 'POST',
      )
      expect(rejectCall).toBeTruthy()
      const body = JSON.parse((rejectCall!.init!.body as string) || '{}')
      expect(body.reason).toBe('Library is closed for inventory that week')
    })
  })
})
