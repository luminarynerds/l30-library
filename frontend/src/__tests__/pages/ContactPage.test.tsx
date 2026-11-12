/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, screen, waitFor } from '@testing-library/react'
import { render } from '../utils/test-utils'
import ContactPage from '@/pages/ContactPage'
import * as supportApi from '@/api/support-api'

vi.mock('@/api/support-api', async () => {
  const actual = await vi.importActual<typeof supportApi>('@/api/support-api')
  return {
    ...actual,
    submitContactMessage: vi.fn(),
  }
})

const mockedSubmit = vi.mocked(supportApi.submitContactMessage)

// Preload English translations before any rendering — vitest setup.ts
// does not preload i18n, and ContactPage's queries-by-label only work when
// the English copy is loaded into the module-level cache.

beforeEach(() => {
  mockedSubmit.mockReset()
})

describe('ContactPage', () => {
  it('submits to /api/v1/support and shows ticket number on success', async () => {
    mockedSubmit.mockResolvedValueOnce({
      ticket_id: '42',
      status: 'open',
      reference_number: 'SUPPORT-2026-ABCD1234',
      message: 'received',
      category: 'referenceHelp',
      response_route: 'reference',
      sla_business_days: 1,
    })

    render(<ContactPage />)

    // Pick a topic group, then a specific category
    fireEvent.click(screen.getByRole('button', { name: /Getting help/i }))
    const select = await screen.findByLabelText(/Subject/i)
    fireEvent.change(select, { target: { value: 'referenceHelp' } })

    // Name + email (email contactMethod is default).
    // Multiple "Email" labels exist (the radio + the text input); target by id.
    fireEvent.change(screen.getByLabelText(/Name/i), { target: { value: 'Maria' } })
    const emailInput = document.getElementById('contact-email') as HTMLInputElement
    fireEvent.change(emailInput, { target: { value: 'maria@example.org' } })
    const messageInput = document.getElementById('contact-message') as HTMLTextAreaElement
    fireEvent.change(messageInput, {
      target: { value: 'Looking for books on Ohio public records law.' },
    })

    fireEvent.click(screen.getByRole('button', { name: /Send Message/i }))

    await waitFor(() => {
      expect(mockedSubmit).toHaveBeenCalledTimes(1)
    })
    expect(mockedSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        category: 'referenceHelp',
        name: 'Maria',
        email: 'maria@example.org',
        contactMethod: 'email',
      })
    )

    // Receipt heading + reference number visible
    expect(await screen.findByText(/Message received/i)).toBeInTheDocument()
    expect(screen.getByText('SUPPORT-2026-ABCD1234')).toBeInTheDocument()
  })

  it('anonymous toggle removes required validation for name/email when category is bookConcern', async () => {
    mockedSubmit.mockResolvedValueOnce({
      ticket_id: '43',
      status: 'open',
      reference_number: 'SUPPORT-2026-ANON1111',
      message: 'received',
      category: 'bookConcern',
      response_route: 'director',
      sla_business_days: 2,
    })

    render(<ContactPage />)

    // Pick "Concerns & complaints" -> bookConcern
    fireEvent.click(screen.getByRole('button', { name: /Concerns/i }))
    const select = await screen.findByLabelText(/Subject/i)
    fireEvent.change(select, { target: { value: 'bookConcern' } })

    // Check the anonymous toggle
    const anonToggle = await screen.findByLabelText(/Submit anonymously/i)
    fireEvent.click(anonToggle)

    // Only message field needs to be filled
    fireEvent.change(screen.getByLabelText(/Message/i), {
      target: { value: 'I have a concern about a book in the YA section.' },
    })

    fireEvent.click(screen.getByRole('button', { name: /Send Message/i }))

    await waitFor(() => {
      expect(mockedSubmit).toHaveBeenCalledTimes(1)
    })
    expect(mockedSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        category: 'bookConcern',
        isAnonymous: true,
        name: undefined,
        email: undefined,
      })
    )
  })

  it('selecting Records Request shows redirect block and hides message + submit', async () => {
    render(<ContactPage />)

    // Civic topic group -> recordsRequest specific category
    fireEvent.click(screen.getByRole('button', { name: /Civic/i }))
    const select = await screen.findByLabelText(/Subject/i)
    fireEvent.change(select, { target: { value: 'recordsRequest' } })

    // Redirect block visible with the right link target
    expect(await screen.findByTestId('contact-records-redirect')).toBeInTheDocument()
    const cta = screen.getByRole('link', { name: /records request form/i })
    expect(cta).toHaveAttribute('href', '/transparency/records-requests')

    // Normal form fields + submit gone
    expect(screen.queryByLabelText(/Message/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Send Message/i })).not.toBeInTheDocument()

    // The submit API was never called
    expect(mockedSubmit).not.toHaveBeenCalled()
  })

  it('switching from recordsRequest to another category restores the form', async () => {
    render(<ContactPage />)

    fireEvent.click(screen.getByRole('button', { name: /Civic/i }))
    const select = await screen.findByLabelText(/Subject/i)
    fireEvent.change(select, { target: { value: 'recordsRequest' } })
    expect(await screen.findByTestId('contact-records-redirect')).toBeInTheDocument()

    fireEvent.change(select, { target: { value: 'accessibility' } })

    expect(screen.queryByTestId('contact-records-redirect')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Send Message/i })).toBeInTheDocument()
  })

  it('under-13 path collapses fields and submits with no identifiers', async () => {
    mockedSubmit.mockResolvedValueOnce({
      ticket_id: '44',
      status: 'open',
      reference_number: 'SUPPORT-2026-KID00000',
      message: 'received',
      category: 'youthFamily',
      response_route: 'youth',
      sla_business_days: 2,
    })

    render(<ContactPage />)

    // Pick "A kid under 13"
    const kidRadio = screen.getByLabelText(/A kid under 13/i)
    fireEvent.click(kidRadio)

    // The COPPA-safe path should NOT show name/email inputs
    expect(screen.queryByLabelText(/Name/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/Email/i, { selector: 'input' })).not.toBeInTheDocument()

    // Just a message box
    const messageBox = screen.getByLabelText(/Your question/i)
    fireEvent.change(messageBox, { target: { value: 'Do you have books about dragons?' } })

    fireEvent.click(screen.getByRole('button', { name: /Send Message/i }))

    await waitFor(() => {
      expect(mockedSubmit).toHaveBeenCalledTimes(1)
    })

    expect(mockedSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        category: 'youthFamily',
        isAnonymous: true,
        contactMethod: 'none',
        name: undefined,
        email: undefined,
        phone: undefined,
      })
    )
  })
})
