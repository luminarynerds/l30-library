/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMockEvent } from '@/__tests__/helpers/testHelpers'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, opt?: Record<string, unknown> | string) =>
      typeof opt === 'string' ? opt : key,
    language: 'en',
    isRTL: false,
  }),
}))

vi.mock('@/features/accessibility/hooks/useAccessibility', () => ({
  useAccessibility: () => ({
    settings: { quietMode: false },
    updateSetting: vi.fn(),
  }),
}))

import FeaturedEventsSection from '../FeaturedEventsSection'

const featured = createMockEvent({ id: 1, title: 'Featured One', is_featured: true, registration_required: false })

describe('FeaturedEventsSection — a11y', () => {
  it('renders each featured event as a passive <article> (no fake clickable role)', () => {
    render(<FeaturedEventsSection events={[featured]} onEventClick={vi.fn()} onRegister={vi.fn()} />)
    const card = screen.getByRole('article')
    expect(card.tagName).toBe('ARTICLE')
    expect(card).not.toHaveAttribute('tabindex')
  })

  it('navigates via a real title button, not a click handler on the card', async () => {
    const user = userEvent.setup()
    const onEventClick = vi.fn()
    render(<FeaturedEventsSection events={[featured]} onEventClick={onEventClick} onRegister={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: 'Featured One' }))
    expect(onEventClick).toHaveBeenCalledTimes(1)
  })
})
