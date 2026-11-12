/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    language: 'en',
    isRTL: false,
  }),
}))

import ViewToggle from '../ViewToggle'

describe('ViewToggle', () => {
  it('renders all four view options, including Linear', () => {
    render(<ViewToggle viewMode="list" onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'events.listView' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'events.calendarView' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'events.agendaView' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'events.linearView' })).toBeInTheDocument()
  })

  it('calls onChange with "linear" when the Linear button is clicked', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<ViewToggle viewMode="list" onChange={onChange} />)
    await user.click(screen.getByRole('button', { name: 'events.linearView' }))
    expect(onChange).toHaveBeenCalledWith('linear')
  })

  it('marks the Linear button pressed only when viewMode is linear', () => {
    render(<ViewToggle viewMode="linear" onChange={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'events.linearView' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'events.listView' })).toHaveAttribute('aria-pressed', 'false')
  })
})
