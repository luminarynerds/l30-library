/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from './utils/test-utils'
import userEvent from '@testing-library/user-event'
import SetupStepName from '@/components/setup/SetupStepName'

const base = {
  library_name: '',
  library_short_name: '',
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

describe('SetupStepName', () => {
  it('captures first and last admin name separately', async () => {
    const onChange = vi.fn()
    render(<SetupStepName config={base} onChange={onChange} onNext={vi.fn()} />)

    await userEvent.type(screen.getByLabelText(/first name/i), 'A')
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ admin_first_name: 'A' }),
    )

    await userEvent.type(screen.getByLabelText(/last name/i), 'B')
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ admin_last_name: 'B' }),
    )
  })

  it('hides the admin account block when hideAdminAccount is set (planner)', () => {
    render(<SetupStepName config={base} onChange={vi.fn()} onNext={vi.fn()} embedded hideAdminAccount />)
    expect(screen.queryByText(/your admin account/i)).toBeNull()
    expect(screen.queryByLabelText(/^password/i)).toBeNull()
  })
})
