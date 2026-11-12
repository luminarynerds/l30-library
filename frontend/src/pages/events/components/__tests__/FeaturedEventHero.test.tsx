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
    settings: { quietMode: false, noFOMO: false },
    updateSetting: vi.fn(),
  }),
}))

vi.mock('@/hooks/useNeurodivergentUX', () => ({
  useNeurodivergentUX: () => ({ shouldHideFOMO: false }),
}))

vi.mock('@/components/ShareButton', () => ({
  default: () => <div data-testid="share-button" />,
}))

import FeaturedEventHero from '../FeaturedEventHero'

const event = createMockEvent({ id: 1, title: 'Hero Event', registration_required: false })

describe('FeaturedEventHero — a11y', () => {
  it('renders the event title as a plain heading, not a button', () => {
    render(<FeaturedEventHero event={event} onEventClick={vi.fn()} onRegister={vi.fn()} />)
    const heading = screen.getByRole('heading', { level: 2, name: 'Hero Event' })
    expect(heading.tagName).toBe('H2')
    // The heading must not also be exposed as a control (no role="button").
    expect(screen.queryByRole('button', { name: 'Hero Event' })).toBeNull()
  })

  it('exposes a single "Learn more" action button that triggers onEventClick', async () => {
    const user = userEvent.setup()
    const onEventClick = vi.fn()
    render(<FeaturedEventHero event={event} onEventClick={onEventClick} onRegister={vi.fn()} />)
    // Registration is off and ShareButton is stubbed, so the lone button is "Learn more".
    const learnMore = screen.getByRole('button')
    await user.click(learnMore)
    expect(onEventClick).toHaveBeenCalledTimes(1)
  })
})
