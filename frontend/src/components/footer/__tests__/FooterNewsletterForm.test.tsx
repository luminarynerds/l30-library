/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, userEvent, waitFor } from '../../../__tests__/utils/test-utils'
import { FooterNewsletterForm } from '../FooterNewsletterForm'

const subscribeMock = vi.fn()
vi.mock('@/api/marketing-api', () => ({
  subscribeToNewsletter: (...args: unknown[]) => subscribeMock(...args),
}))

const INVALID_MSG = 'Please enter a valid email address.'

describe('FooterNewsletterForm', () => {
  beforeEach(() => {
    subscribeMock.mockReset()
  })

  it('renders the submit button enabled on first paint (no low-contrast disabled state)', () => {
    render(<FooterNewsletterForm />)
    expect(screen.getByRole('button', { name: 'Subscribe' })).toBeEnabled()
  })

  it('rejects an invalid email without calling the API and announces the error accessibly', async () => {
    const user = userEvent.setup()
    render(<FooterNewsletterForm />)
    await user.type(screen.getByLabelText('Enter your email'), 'not-an-email')
    await user.click(screen.getByRole('button', { name: 'Subscribe' }))

    expect(await screen.findByText(INVALID_MSG)).toBeInTheDocument()
    expect(subscribeMock).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Enter your email')).toHaveAttribute('aria-invalid', 'true')
  })

  it('submits a valid email and shows success', async () => {
    subscribeMock.mockResolvedValue({})
    const user = userEvent.setup()
    render(<FooterNewsletterForm />)
    await user.type(screen.getByLabelText('Enter your email'), 'reader@example.com')
    await user.click(screen.getByRole('button', { name: 'Subscribe' }))

    await waitFor(() =>
      expect(subscribeMock).toHaveBeenCalledWith({
        email: 'reader@example.com',
        consent_source: 'newsletter_form',
      }),
    )
    expect(await screen.findByText(/Thanks for subscribing/)).toBeInTheDocument()
  })

  it('clears the invalid message once the user edits the field', async () => {
    const user = userEvent.setup()
    render(<FooterNewsletterForm />)
    await user.click(screen.getByRole('button', { name: 'Subscribe' }))
    expect(await screen.findByText(INVALID_MSG)).toBeInTheDocument()

    await user.type(screen.getByLabelText('Enter your email'), 'r')
    await waitFor(() => expect(screen.queryByText(INVALID_MSG)).not.toBeInTheDocument())
  })
})
