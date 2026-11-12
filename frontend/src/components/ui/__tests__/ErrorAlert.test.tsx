/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ErrorAlert } from '../ErrorAlert'

// Mock branding so useBranding doesn't require a provider in tests.
vi.mock('@/contexts/BrandingContext', () => ({
  useBranding: () => ({ contact_email: 'support@example.org' }),
}))

// Stub the escalation modal so we can assert it was opened with the right
// context without depending on its full DOM and the support API.
vi.mock('@/components/EscalationModal', () => ({
  default: ({ isOpen, context }: { isOpen?: boolean; context?: string }) =>
    isOpen ? <div data-testid="escalation-modal" data-context={context} /> : null,
}))

function renderAlert(props: Partial<React.ComponentProps<typeof ErrorAlert>> = {}) {
  return render(
    <MemoryRouter initialEntries={['/account/settings']}>
      <ErrorAlert
        title="Couldn't save your changes"
        message="We're having a temporary issue. Your work is safe."
        showSupport
        errorCode="ERR_500"
        {...props}
      />
    </MemoryRouter>
  )
}


// Preload English translations. vitest setup.ts does not preload i18n,
// and t() returns raw dotted-path keys when no language is loaded,
// breaking assertions that match resolved English strings.

describe('ErrorAlert contact support', () => {
  it('opens the escalation modal with error context when clicked', async () => {
    const user = userEvent.setup()
    renderAlert()

    expect(screen.queryByTestId('escalation-modal')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /contact support/i }))

    const modal = await screen.findByTestId('escalation-modal')
    const context = modal.getAttribute('data-context') ?? ''
    expect(context).toContain("Couldn't save your changes")
    expect(context).toContain('ERR_500')
    expect(context).toContain('/account/settings')
  })
})
