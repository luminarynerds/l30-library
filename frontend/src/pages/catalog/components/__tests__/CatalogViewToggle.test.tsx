/// <reference types="@testing-library/jest-dom" />
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * The toggle is a pair of plain aria-pressed buttons (not a tablist), and
 * "disabled" must be real disabled attributes, keyboard included — not just
 * opacity + pointer-events.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CatalogViewToggle from '../CatalogViewToggle'

vi.mock('@/i18n', () => ({
  t: (key: string) => key,
}))

describe('CatalogViewToggle — button semantics', () => {
  it('uses aria-pressed buttons, not tabs', () => {
    render(<CatalogViewToggle viewMode="list" onViewChange={vi.fn()} />)

    expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
    expect(screen.queryByRole('tab')).not.toBeInTheDocument()

    const list = screen.getByRole('button', { name: /listView/ })
    const grid = screen.getByRole('button', { name: /gridView/ })
    expect(list).toHaveAttribute('aria-pressed', 'true')
    expect(grid).toHaveAttribute('aria-pressed', 'false')
  })

  it('fires onViewChange when enabled', async () => {
    const user = userEvent.setup()
    const onViewChange = vi.fn()
    render(<CatalogViewToggle viewMode="list" onViewChange={onViewChange} />)

    await user.click(screen.getByRole('button', { name: /gridView/ }))
    expect(onViewChange).toHaveBeenCalledWith('grid')
  })

  it('is truly inert when disabled (real disabled attribute, keyboard included)', async () => {
    const user = userEvent.setup()
    const onViewChange = vi.fn()
    render(<CatalogViewToggle viewMode="list" onViewChange={onViewChange} disabled />)

    const grid = screen.getByRole('button', { name: /gridView/ })
    expect(grid).toBeDisabled()

    await user.click(grid)
    // Keyboard path: disabled buttons are not focusable/activatable.
    grid.focus()
    expect(document.activeElement).not.toBe(grid)
    await user.keyboard('{Enter}')

    expect(onViewChange).not.toHaveBeenCalled()
  })
})
