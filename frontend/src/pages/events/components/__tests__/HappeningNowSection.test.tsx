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
    settings: { quietMode: false, noFOMO: false, noUrgentLanguage: false },
    updateSetting: vi.fn(),
  }),
}))

import HappeningNowSection from '../HappeningNowSection'

// Absolute local times so isToday() is stable regardless of when the suite runs.
function atLocalTime(daysFromToday: number, hour: number): string {
  const d = new Date()
  d.setDate(d.getDate() + daysFromToday)
  d.setHours(hour, 0, 0, 0)
  return d.toISOString()
}

const todayEvent = createMockEvent({ id: 1, title: 'Today Event', start_time: atLocalTime(0, 9), registration_required: true, spots_remaining: 5 })
const secondTodayEvent = createMockEvent({ id: 2, title: 'Second Today Event', start_time: atLocalTime(0, 13), registration_required: false })

describe('HappeningNowSection — a11y', () => {
  it('renders today tiles as passive <article>s (no fake clickable role)', () => {
    render(<HappeningNowSection events={[todayEvent, secondTodayEvent]} onEventClick={vi.fn()} onRegister={vi.fn()} />)
    const articles = screen.getAllByRole('article')
    expect(articles.length).toBeGreaterThanOrEqual(2)
    articles.forEach((a) => {
      expect(a.tagName).toBe('ARTICLE')
      expect(a).not.toHaveAttribute('tabindex')
    })
  })

  it('opens an event via its title button, not a click on the tile', async () => {
    const user = userEvent.setup()
    const onEventClick = vi.fn()
    render(<HappeningNowSection events={[todayEvent, secondTodayEvent]} onEventClick={onEventClick} onRegister={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: 'Today Event' }))
    await user.click(screen.getByRole('button', { name: 'Second Today Event' }))
    expect(onEventClick).toHaveBeenCalledTimes(2)
  })

  it('register button triggers onRegister', async () => {
    const user = userEvent.setup()
    const onRegister = vi.fn()
    render(<HappeningNowSection events={[todayEvent, secondTodayEvent]} onEventClick={vi.fn()} onRegister={onRegister} />)
    await user.click(screen.getByRole('button', { name: 'events.register' }))
    expect(onRegister).toHaveBeenCalledTimes(1)
  })
})
