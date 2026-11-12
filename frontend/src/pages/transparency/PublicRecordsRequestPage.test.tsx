/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (key: string, vars?: Record<string, string>) => {
    if (vars) return `${key}:${JSON.stringify(vars)}`
    return key
  }}),
}))

const mockSubmit = vi.fn()
const mockLog = vi.fn()
vi.mock('@/api/public-records-api', () => ({
  submitPublicRecordsRequest: (...args: unknown[]) => mockSubmit(...args),
  getPublicDisclosureLog: (...args: unknown[]) => mockLog(...args),
}))

import PublicRecordsRequestPage from './PublicRecordsRequestPage'

const renderPage = (search = '') =>
  render(
    <MemoryRouter initialEntries={[`/transparency/records-requests${search}`]}>
      <PublicRecordsRequestPage />
    </MemoryRouter>,
  )

describe('PublicRecordsRequestPage', () => {
  beforeEach(() => {
    mockSubmit.mockReset()
    mockLog.mockReset()
    mockLog.mockResolvedValue([])
  })

  it('renders form heading and disclosure log', async () => {
    renderPage()
    expect(screen.getByText('publicRecords.pageTitle')).toBeTruthy()
    expect(screen.getByText('publicRecords.log.heading')).toBeTruthy()
  })

  it('shows meeting context chip when meeting_id query param is set', () => {
    renderPage('?meeting_id=5')
    expect(screen.getByText(/meeting #5/)).toBeTruthy()
  })

  it('submit happy path shows success card', async () => {
    mockSubmit.mockResolvedValue({
      tracking_number: 'ORR-2026-001',
      response_deadline: '2026-06-18',
      status: 'received',
    })

    renderPage()

    fireEvent.change(screen.getByLabelText('publicRecords.form.nameLabel'), {
      target: { value: 'Jane Patron' },
    })
    fireEvent.change(screen.getByLabelText('publicRecords.form.emailLabel'), {
      target: { value: 'jane@example.com' },
    })
    fireEvent.change(screen.getByLabelText('publicRecords.form.descriptionLabel'), {
      target: { value: 'I want the board minutes from last year.' },
    })

    fireEvent.submit(screen.getByRole('form', { name: /public records request form/i }))

    await waitFor(() => {
      expect(screen.getByText('publicRecords.form.successTitle')).toBeTruthy()
    })
    expect(mockSubmit).toHaveBeenCalledTimes(1)
  })

  it('shows error message on submission failure', async () => {
    mockSubmit.mockRejectedValue({ message: 'Server error' })

    renderPage()

    fireEvent.change(screen.getByLabelText('publicRecords.form.nameLabel'), {
      target: { value: 'Jane Patron' },
    })
    fireEvent.change(screen.getByLabelText('publicRecords.form.emailLabel'), {
      target: { value: 'jane@example.com' },
    })
    fireEvent.change(screen.getByLabelText('publicRecords.form.descriptionLabel'), {
      target: { value: 'I want the board minutes from last year.' },
    })

    fireEvent.submit(screen.getByRole('form', { name: /public records request form/i }))

    await waitFor(() => {
      expect(screen.getByText(/publicRecords.form.errorTitle/)).toBeTruthy()
    })
  })
})
