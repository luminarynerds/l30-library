/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import StaffMarcMacrosPage from './StaffMarcMacrosPage'
import {
  listMarcMacros,
  getMarcMacroTargets,
  createMarcMacro,
} from '../../api/marc-macros-api'

vi.mock('../../api/marc-macros-api', () => ({
  listMarcMacros: vi.fn(),
  getMarcMacroTargets: vi.fn(),
  createMarcMacro: vi.fn(),
  updateMarcMacro: vi.fn(),
  deleteMarcMacro: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({
    children,
    actions,
  }: {
    children: React.ReactNode
    actions?: React.ReactNode
  }) => (
    <div>
      {actions}
      {children}
    </div>
  ),
}))

describe('StaffMarcMacrosPage a11y', () => {
  beforeEach(() => {
    ;(listMarcMacros as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [] })
    ;(getMarcMacroTargets as ReturnType<typeof vi.fn>).mockResolvedValue({
      '245$a': 'Title',
    })
  })

  async function openEditor() {
    render(<StaffMarcMacrosPage />)
    fireEvent.click(await screen.findByRole('button', { name: /new macro/i }))
    return await screen.findByRole('dialog')
  }

  it('renders the editor as an accessible dialog with a heading', async () => {
    const dialog = await openEditor()
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(
      within(dialog).getByRole('heading', { name: /new macro/i })
    ).toBeInTheDocument()
  })

  it('labels the macro step operation and target-field controls', async () => {
    const dialog = await openEditor()
    expect(within(dialog).getByLabelText('Operation')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Target field')).toBeInTheDocument()
    // find/replace inputs appear when op is find_replace
    fireEvent.change(within(dialog).getByLabelText('Operation'), {
      target: { value: 'find_replace' },
    })
    expect(within(dialog).getByLabelText('Find text')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('Replace with')).toBeInTheDocument()
  })

  it('surfaces a save failure in an in-modal alert', async () => {
    ;(createMarcMacro as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Server exploded')
    )
    const dialog = await openEditor()
    fireEvent.change(within(dialog).getByLabelText('Operation'), {
      target: { value: 'clear' },
    })
    // Name field is the first textbox in the dialog body
    const nameInput = within(dialog).getAllByRole('textbox')[0]!
    fireEvent.change(nameInput, { target: { value: 'My macro' } })
    fireEvent.click(within(dialog).getByRole('button', { name: /^save$/i }))
    await waitFor(() =>
      expect(within(dialog).getByRole('alert')).toHaveTextContent('Server exploded')
    )
  })
})
