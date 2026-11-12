/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ProgramPartnerForm from '../ProgramPartnerForm'
import type { EventProgramPartner } from '@/api/domains/services/program-partners-api'

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    language: 'en',
    t: (key: string, paramsOrFallback?: Record<string, unknown> | string) =>
      typeof paramsOrFallback === 'string' ? paramsOrFallback : key,
    isRTL: false,
    setLanguage: vi.fn(),
  }),
}))

const EXISTING: EventProgramPartner = {
  id: 7,
  name: 'Friends of the Library',
  slug: 'friends_of_the_library',
  website: 'https://friends.example.org',
  contact_email: 'friends@example.org',
  contact_phone: '555-0100',
  notes: 'Long-time partner',
  is_active: true,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-05-01T00:00:00Z',
}

describe('ProgramPartnerForm — create mode', () => {
  it('blocks submit and surfaces inline name error when name is empty', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<ProgramPartnerForm mode="create" onSubmit={onSubmit} onCancel={() => {}} />)

    await user.click(screen.getByRole('button', { name: /Create partner/ }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText(/Name is required/)).toBeInTheDocument()
  })

  it('rejects invalid website URL with inline error', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<ProgramPartnerForm mode="create" onSubmit={onSubmit} onCancel={() => {}} />)

    await user.type(screen.getByLabelText(/Name/, { selector: 'input' }), 'New Partner')
    await user.type(screen.getByLabelText(/Website/, { selector: 'input' }), 'not-a-url')
    await user.click(screen.getByRole('button', { name: /Create partner/ }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText(/Website must start with http/)).toBeInTheDocument()
  })

  it('rejects invalid contact email with inline error', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<ProgramPartnerForm mode="create" onSubmit={onSubmit} onCancel={() => {}} />)

    await user.type(screen.getByLabelText(/Name/, { selector: 'input' }), 'New Partner')
    await user.type(screen.getByLabelText(/Contact email/, { selector: 'input' }), 'nope')
    await user.click(screen.getByRole('button', { name: /Create partner/ }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText(/Enter a valid email/)).toBeInTheDocument()
  })

  it('submits create payload when valid; is_active defaults to true', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<ProgramPartnerForm mode="create" onSubmit={onSubmit} onCancel={() => {}} />)

    await user.type(screen.getByLabelText(/Name/, { selector: 'input' }), 'New Partner')
    await user.type(screen.getByLabelText(/Website/, { selector: 'input' }), 'https://np.example')
    await user.type(screen.getByLabelText(/Contact email/, { selector: 'input' }), 'np@example.org')
    await user.click(screen.getByRole('button', { name: /Create partner/ }))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith({
      name: 'New Partner',
      website: 'https://np.example',
      contact_email: 'np@example.org',
      contact_phone: null,
      notes: null,
      is_active: true,
    })
  })

  it('does NOT show the is_active checkbox in create mode', () => {
    render(<ProgramPartnerForm mode="create" onSubmit={vi.fn()} onCancel={() => {}} />)
    expect(screen.queryByLabelText(/^Active$/)).not.toBeInTheDocument()
  })
})

describe('ProgramPartnerForm — edit mode', () => {
  it('pre-fills fields from initial values', () => {
    render(
      <ProgramPartnerForm
        mode="edit"
        initial={EXISTING}
        onSubmit={vi.fn()}
        onCancel={() => {}}
      />,
    )

    expect(screen.getByLabelText(/Name/, { selector: 'input' })).toHaveValue('Friends of the Library')
    expect(screen.getByLabelText(/Website/, { selector: 'input' })).toHaveValue('https://friends.example.org')
    expect(screen.getByLabelText(/Contact email/, { selector: 'input' })).toHaveValue('friends@example.org')
    expect(screen.getByLabelText(/Contact phone/, { selector: 'input' })).toHaveValue('555-0100')
    expect(screen.getByLabelText(/^Active$/)).toBeChecked()
  })

  it('submits PATCH-style payload including is_active', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(
      <ProgramPartnerForm
        mode="edit"
        initial={EXISTING}
        onSubmit={onSubmit}
        onCancel={() => {}}
      />,
    )

    const nameInput = screen.getByLabelText(/Name/, { selector: 'input' })
    await user.clear(nameInput)
    await user.type(nameInput, 'Friends of LSC')
    await user.click(screen.getByLabelText(/^Active$/))
    await user.click(screen.getByRole('button', { name: /Save changes/ }))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith({
      name: 'Friends of LSC',
      website: 'https://friends.example.org',
      contact_email: 'friends@example.org',
      contact_phone: '555-0100',
      notes: 'Long-time partner',
      is_active: false,
    })
  })
})
