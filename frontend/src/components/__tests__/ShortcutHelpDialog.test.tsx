/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for the staff keyboard-shortcut help dialog.
 *
 * Pins the WCAG behaviors added in the header WCAG-followups pass:
 *  - 2.4.3 focus order: tab cycles within the dialog (focus trap)
 *  - 2.1.2 no keyboard trap (Escape lets the user exit)
 *  - 4.1.2 name/role/value: dialog is labelled by its heading, not aria-label
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { ShortcutHelpDialog } from '../Layout'

const renderDialog = () => {
  const onClose = vi.fn()
  const utils = render(
    <MemoryRouter>
      <ShortcutHelpDialog onClose={onClose} />
    </MemoryRouter>,
  )
  return { ...utils, onClose, user: userEvent.setup() }
}

describe('ShortcutHelpDialog', () => {
  it('is labelled by its heading (aria-labelledby, not aria-label)', () => {
    renderDialog()
    const dialog = screen.getByRole('dialog')
    const labelledBy = dialog.getAttribute('aria-labelledby')
    expect(labelledBy).toBeTruthy()
    expect(dialog).not.toHaveAttribute('aria-label')
    const heading = document.getElementById(labelledBy!)
    expect(heading).not.toBeNull()
    expect(heading!.tagName).toBe('H2')
    expect(heading!.textContent).toMatch(/keyboard shortcuts/i)
  })

  it('closes via Escape (no keyboard trap)', async () => {
    const { user, onClose } = renderDialog()
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalled()
  })

  it('keeps Tab focus inside the dialog', async () => {
    const { user } = renderDialog()
    const closeButton = await screen.findByRole('button', { name: /close/i })
    // Focus is set to the first focusable on mount (the Close button is the
    // only focusable inside). Tab from there must wrap back to itself, not
    // escape to <body>.
    // Allow the requestAnimationFrame+setTimeout(0) inside useFocusTrap to run.
    await new Promise((r) => setTimeout(r, 50))
    expect(closeButton).toHaveFocus()
    await user.tab()
    expect(document.activeElement).toBe(closeButton)
  })
})
