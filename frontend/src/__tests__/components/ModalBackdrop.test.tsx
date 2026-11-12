/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ModalBackdrop } from '../../components/ui/ModalBackdrop'

describe('ModalBackdrop a11y', () => {
  it('renders role=dialog with aria-modal', () => {
    render(
      <ModalBackdrop onClose={() => {}} title="Hello">
        <button>Inner</button>
      </ModalBackdrop>
    )
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })

  it('uses labelledBy prop to reference a visible heading id', () => {
    render(
      <ModalBackdrop onClose={() => {}} labelledBy="my-heading">
        <h2 id="my-heading">Create Community Hub</h2>
        <button>Inner</button>
      </ModalBackdrop>
    )
    const dialog = screen.getByRole('dialog', { name: 'Create Community Hub' })
    expect(dialog).toHaveAttribute('aria-labelledby', 'my-heading')
  })

  it('exposes describedBy via aria-describedby', () => {
    render(
      <ModalBackdrop
        onClose={() => {}}
        labelledBy="t"
        describedBy="d"
      >
        <h2 id="t">Title</h2>
        <p id="d">Supplementary description.</p>
        <button>Go</button>
      </ModalBackdrop>
    )
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-describedby', 'd')
    expect(dialog).toHaveAccessibleDescription('Supplementary description.')
  })

  it('falls back to sr-only title span when only `title` prop is provided', () => {
    render(
      <ModalBackdrop onClose={() => {}} title="Legacy">
        <button>Inner</button>
      </ModalBackdrop>
    )
    const dialog = screen.getByRole('dialog', { name: 'Legacy' })
    expect(dialog.getAttribute('aria-labelledby')).toBeTruthy()
  })

  it('Escape key triggers onClose', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(
      <ModalBackdrop onClose={onClose} title="x">
        <button autoFocus>Inner</button>
      </ModalBackdrop>
    )
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('Escape is suppressed when dismissible is false', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(
      <ModalBackdrop onClose={onClose} title="x" dismissible={false}>
        <button autoFocus>Inner</button>
      </ModalBackdrop>
    )
    await user.keyboard('{Escape}')
    expect(onClose).not.toHaveBeenCalled()
  })

  it('restores focus to the previously focused element when the modal unmounts', async () => {
    const user = userEvent.setup()

    function Harness() {
      const [open, setOpen] = useState(false)
      return (
        <>
          <button data-testid="opener" onClick={() => setOpen(true)}>Open</button>
          {open && (
            <ModalBackdrop onClose={() => setOpen(false)} labelledBy="h">
              <h2 id="h">Title</h2>
              <button onClick={() => setOpen(false)}>Close</button>
            </ModalBackdrop>
          )}
        </>
      )
    }

    render(<Harness />)
    const opener = screen.getByTestId('opener')
    opener.focus()
    expect(opener).toHaveFocus()

    await user.click(opener)
    await screen.findByRole('dialog')

    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
    await waitFor(() => {
      expect(opener).toHaveFocus()
    })
  })
})
