/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, userEvent } from '@/__tests__/utils/test-utils'
import SetupStepReview from '../SetupStepReview'

const baseConfig = {
  library_name: 'Test Library',
  library_short_name: 'TL',
  contact_email: 'c@test.org',
  phone: '555',
  address_line1: '1 St',
  address_line2: '',
  admin_first_name: 'A',
  admin_last_name: 'B',
  admin_email: 'admin@test.org',
  admin_password: 'pw',
  feature_preset: 'small_library' as const,
  feature_overrides: {},
  primary_color: '#111111',
  accent_color: '#222222',
  hero_title: 'H',
  hero_subtitle: 'S',
  tagline: 'T',
}

describe('SetupStepReview launch button', () => {
  it('exits the Launching... disabled state after a successful submit', async () => {
    let resolveSubmit: () => void = () => {}
    const onSubmit = vi.fn(() => new Promise<void>((r) => { resolveSubmit = r }))
    render(<SetupStepReview config={baseConfig} onBack={vi.fn()} onSubmit={onSubmit} />)

    const btn = screen.getByRole('button', { name: /launch your library/i })
    await userEvent.click(btn)

    expect(screen.getByRole('button', { name: /launching/i })).toBeDisabled()

    resolveSubmit()

    await waitFor(() => {
      const b = screen.getByRole('button', { name: /launch your library/i })
      expect(b).not.toBeDisabled()
    })
    expect(onSubmit).toHaveBeenCalledTimes(1)
  })

  it('resets the button and surfaces an error after a failed submit', async () => {
    const onSubmit = vi.fn(() => Promise.reject(new Error('boom')))
    render(<SetupStepReview config={baseConfig} onBack={vi.fn()} onSubmit={onSubmit} />)

    await userEvent.click(screen.getByRole('button', { name: /launch your library/i }))

    await waitFor(() => {
      expect(screen.getByText(/boom/i)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /launch your library/i })).not.toBeDisabled()
  })
})
