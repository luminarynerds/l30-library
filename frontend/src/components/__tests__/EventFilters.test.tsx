/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// `t(key, fallback)` -> fallback string when one is given, else the key, so
// the panel's accessibility labels resolve to their English fallbacks. The
// impl is inlined in each factory because vi.mock is hoisted above consts.
vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, opt?: Record<string, unknown> | string) =>
      typeof opt === 'string' ? opt : key,
    language: 'en',
    isRTL: false,
  }),
}))
vi.mock('@/i18n', () => ({
  t: (key: string, opt?: Record<string, unknown> | string) =>
    typeof opt === 'string' ? opt : key,
}))

import EventFilters from '../EventFilters'
import type { EventFilters as Filters } from '@/api/api'

function Harness({ initial = {} }: { initial?: Filters }) {
  const [filters, setFilters] = useState<Filters>(initial)
  return <EventFilters filters={filters} onChange={setFilters} />
}

async function expandAccessibilitySection(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: /accessibility provisions/i }))
}

describe('EventFilters — accessibility provisions section', () => {
  it('renders an Accessibility provisions filter section', () => {
    render(<Harness />)
    expect(
      screen.getByRole('button', { name: /accessibility provisions/i })
    ).toBeInTheDocument()
  })

  it('selecting a provision marks its chip pressed', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await expandAccessibilitySection(user)
    const wheelchair = screen.getByRole('button', { name: 'Wheelchair accessible' })
    expect(wheelchair.getAttribute('aria-pressed')).toBe('false')
    await user.click(wheelchair)
    expect(
      screen.getByRole('button', { name: 'Wheelchair accessible' }).getAttribute('aria-pressed')
    ).toBe('true')
  })

  it('is multi-select with AND semantics — two provisions stay pressed together', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await expandAccessibilitySection(user)
    await user.click(screen.getByRole('button', { name: 'Wheelchair accessible' }))
    await user.click(screen.getByRole('button', { name: 'ASL provided' }))
    expect(
      screen.getByRole('button', { name: 'Wheelchair accessible' }).getAttribute('aria-pressed')
    ).toBe('true')
    expect(
      screen.getByRole('button', { name: 'ASL provided' }).getAttribute('aria-pressed')
    ).toBe('true')
  })

  it('deselecting a provision clears it', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await expandAccessibilitySection(user)
    const sensory = screen.getByRole('button', { name: 'Sensory-friendly' })
    await user.click(sensory)
    expect(
      screen.getByRole('button', { name: 'Sensory-friendly' }).getAttribute('aria-pressed')
    ).toBe('true')
    await user.click(screen.getByRole('button', { name: 'Sensory-friendly' }))
    expect(
      screen.getByRole('button', { name: 'Sensory-friendly' }).getAttribute('aria-pressed')
    ).toBe('false')
  })

  it('shows a removable active-filter pill for a selected provision', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await expandAccessibilitySection(user)
    await user.click(screen.getByRole('button', { name: 'Wheelchair accessible' }))
    // The active-pills row exposes a dedicated remove button for the provision.
    const removePill = screen.getByRole('button', {
      name: /remove accessibility filter: wheelchair accessible/i,
    })
    await user.click(removePill)
    expect(
      screen.getByRole('button', { name: 'Wheelchair accessible' }).getAttribute('aria-pressed')
    ).toBe('false')
  })
})
