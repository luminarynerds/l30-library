/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, userEvent, waitFor } from '@/__tests__/utils/test-utils'
import { ConfirmDialog } from '../ConfirmDialog'

describe('ConfirmDialog', () => {
  it('does not call onConfirm until the confirm button is pressed', async () => {
    const onConfirm = vi.fn()
    const user = userEvent.setup()
    render(
      <ConfirmDialog
        open
        title="Waive fines?"
        body="Waives $12.50 for 3 patrons."
        confirmLabel="Waive fines"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />
    )
    expect(onConfirm).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Waive fines' }))
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it('Escape cancels, never confirms', async () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    const user = userEvent.setup()
    render(
      <ConfirmDialog
        open
        title="t"
        body="b"
        confirmLabel="Go"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    )
    await user.keyboard('{Escape}')
    expect(onCancel).toHaveBeenCalled()
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('renders nothing when open is false', () => {
    render(
      <ConfirmDialog
        open={false}
        title="t"
        body="b"
        confirmLabel="Go"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('focuses the Cancel button when tone is danger', async () => {
    render(
      <ConfirmDialog
        open
        title="Delete template?"
        body="This can't be undone."
        confirmLabel="Delete"
        tone="danger"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    const cancelButton = await screen.findByRole('button', { name: 'Cancel' })
    await waitFor(() => expect(cancelButton).toHaveFocus())
  })
})
