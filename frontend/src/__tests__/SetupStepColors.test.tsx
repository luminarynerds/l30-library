/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from './utils/test-utils'
import userEvent from '@testing-library/user-event'
import SetupStepColors from '@/components/setup/SetupStepColors'

const base = {
  library_name: 'Test Library',
  library_short_name: 'TL',
  contact_email: '',
  phone: '',
  address_line1: '',
  address_line2: '',
  admin_first_name: '',
  admin_last_name: '',
  admin_email: '',
  admin_password: '',
  feature_preset: 'small_library' as const,
  feature_overrides: {},
  primary_color: '#8B5E5E',
  accent_color: '#D49898',
  hero_title: '',
  hero_subtitle: '',
  tagline: '',
}

describe('SetupStepColors', () => {
  it('does not commit an invalid/short hex but commits a complete 6-hex', async () => {
    const onChange = vi.fn()
    render(<SetupStepColors config={base} onChange={onChange} onBack={vi.fn()} onNext={vi.fn()} embedded />)

    // The free-text hex inputs live inside the collapsed Custom Colors accordion.
    await userEvent.click(screen.getByRole('button', { name: /custom colors/i }))

    const primary = screen.getByTestId('primary-hex-input')

    await userEvent.clear(primary)
    await userEvent.type(primary, '#ff')
    expect(onChange).not.toHaveBeenCalledWith(
      expect.objectContaining({ primary_color: '#ff' }),
    )

    await userEvent.clear(primary)
    await userEvent.type(primary, '#123456')
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ primary_color: '#123456' }),
    )
  })
})
