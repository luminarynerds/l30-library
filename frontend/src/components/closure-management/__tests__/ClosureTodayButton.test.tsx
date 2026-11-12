/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, within } from '../../../__tests__/utils/test-utils'
import userEvent from '@testing-library/user-event'
import { CloseTodayButton } from '../CloseTodayButton'

// This test used to render an inline stub (a bare <button>Close Today</button>
// with none of the described behavior implemented) because the real component
// "doesn't exist yet". It does now -- src/components/closure-management/
// CloseTodayButton.tsx -- named CloseTodayButton (not ClosureTodayButton).
// Wire the test to the real thing.

// Mock the API call
vi.mock('../../../api/branch-api', () => ({
  createBranchClosure: vi.fn(),
}))

describe('ClosureTodayButton', () => {
  const mockOnSuccess = vi.fn()
  const mockOnError = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the close today button', () => {
    render(
      <CloseTodayButton
        branchId={1}
        onSuccess={mockOnSuccess}
        onError={mockOnError}
      />
    )

    expect(screen.getByRole('button', { name: /close today/i })).toBeInTheDocument()
  })

  it('opens modal when button is clicked', async () => {
    const user = userEvent.setup()

    render(
      <CloseTodayButton
        branchId={1}
        onSuccess={mockOnSuccess}
        onError={mockOnError}
      />
    )

    const button = screen.getByRole('button', { name: /close today/i })
    await user.click(button)

    // ModalBackdrop's title prop also renders a duplicate sr-only span with
    // the same text (see ModalBackdrop.tsx: "avoids the duplicate sr-only
    // span" -- CloseTodayButton doesn't use the preferred labelledBy form),
    // so match the visible heading specifically rather than any text node.
    expect(
      await screen.findByRole('heading', { name: /close branch today/i }),
    ).toBeInTheDocument()
  })

  it('requires a reason to submit', async () => {
    const user = userEvent.setup()

    render(
      <CloseTodayButton
        branchId={1}
        onSuccess={mockOnSuccess}
        onError={mockOnError}
      />
    )

    const openButton = screen.getByRole('button', { name: /close today/i })
    await user.click(openButton)

    // Scope to the dialog: the trigger button behind it is still in the DOM
    // and shares the same "Close Today" accessible name as the modal's
    // submit button.
    const dialog = await screen.findByRole('alertdialog')
    const submitButton = within(dialog).getByRole('button', { name: /close today/i })
    expect(submitButton).toBeDisabled()
  })

  it('enables submit when reason is entered', async () => {
    const user = userEvent.setup()

    render(
      <CloseTodayButton
        branchId={1}
        onSuccess={mockOnSuccess}
        onError={mockOnError}
      />
    )

    const openButton = screen.getByRole('button', { name: /close today/i })
    await user.click(openButton)

    // The reason field's visible label isn't programmatically associated
    // (no htmlFor/id), so match its actual placeholder copy instead.
    const dialog = await screen.findByRole('alertdialog')
    const reasonInput = within(dialog).getByPlaceholderText(/emergency, equipment failure/i)
    await user.type(reasonInput, 'Emergency')

    // The submit button should now be enabled
    const submitButton = within(dialog).getByRole('button', { name: /close today/i })
    expect(submitButton).not.toBeDisabled()
  })

  it('has checkboxes for notification options', async () => {
    const user = userEvent.setup()

    render(
      <CloseTodayButton
        branchId={1}
        onSuccess={mockOnSuccess}
        onError={mockOnError}
      />
    )

    const openButton = screen.getByRole('button', { name: /close today/i })
    await user.click(openButton)

    await screen.findByRole('alertdialog')
    expect(
      screen.getByRole('checkbox', { name: /patrons and staff/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('checkbox', { name: /events/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('checkbox', { name: /external services/i })
    ).toBeInTheDocument()
  })

  it('closes modal on cancel', async () => {
    const user = userEvent.setup()

    render(
      <CloseTodayButton
        branchId={1}
        onSuccess={mockOnSuccess}
        onError={mockOnError}
      />
    )

    const openButton = screen.getByRole('button', { name: /close today/i })
    await user.click(openButton)

    expect(
      await screen.findByRole('heading', { name: /close branch today/i }),
    ).toBeInTheDocument()

    const cancelButton = screen.getByRole('button', { name: /cancel/i })
    await user.click(cancelButton)

    expect(screen.queryByText(/close branch today/i)).not.toBeInTheDocument()
  })
})
