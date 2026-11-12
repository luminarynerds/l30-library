/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Regressions from combining the Radix Select rewrite with the custom Dialog
 * focus trap (a11y sweep 2026-07-04):
 *  - #1: a Select nested in a Dialog was keyboard-unusable because its listbox
 *        portalled to <body>, outside the focus trap, which yanked focus back.
 *  - #2: Escape closed the whole Dialog even when it should only dismiss the
 *        open Select (Dialog ignored event.defaultPrevented).
 */
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { Dialog, DialogContent, DialogTitle } from '../dialog'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../select'

function Harness({ onOpenChange = vi.fn() }: { onOpenChange?: (o: boolean) => void }) {
  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogTitle>Log Volunteer Hours</DialogTitle>
        <Select>
          <SelectTrigger aria-label="Activity type">
            <SelectValue placeholder="Pick one" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="shelving">Shelving</SelectItem>
            <SelectItem value="programs">Programs</SelectItem>
          </SelectContent>
        </Select>
      </DialogContent>
    </Dialog>
  )
}

describe('Dialog + Select integration', () => {
  it('#1: an open Select portals inside the dialog subtree, not to <body>', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    const trigger = screen.getByRole('combobox', { name: 'Activity type' })
    trigger.focus()
    await user.keyboard('{Enter}')
    const listbox = await screen.findByRole('listbox')
    const presentation = document.querySelector('[role="presentation"]')
    expect(presentation).not.toBeNull()
    // The fix: listbox mounts inside the focus-trap subtree so focus isn't stolen.
    expect(presentation!.contains(listbox)).toBe(true)
    expect(listbox.parentElement).not.toBe(document.body)
  })

  it('#2: Escape does not close the dialog when a nested layer prevented default', () => {
    const onOpenChange = vi.fn()
    render(<Harness onOpenChange={onOpenChange} />)

    // Simulate the open Select handling Escape first (Radix preventDefault in the
    // capture phase, before the dialog's document-level bubble listener).
    const swallow = (e: Event) => e.preventDefault()
    document.addEventListener('keydown', swallow, true)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onOpenChange).not.toHaveBeenCalled()
    document.removeEventListener('keydown', swallow, true)

    // With nothing else handling it, Escape still closes the dialog.
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
