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

import SeriesEventGroup from '../SeriesEventGroup'

// All-drop-in series: no occurrence takes registration.
const group = {
  series_id: 's1',
  series_name: 'Story Series',
  events: [
    createMockEvent({ id: 1, title: 'Week One', start_time: '2026-08-01T18:00:00Z', registration_required: false }),
    createMockEvent({ id: 2, title: 'Week Two', start_time: '2026-08-08T18:00:00Z', registration_required: false }),
  ],
}

// Mixed series: at least one occurrence takes registration.
const regGroup = {
  series_id: 's2',
  series_name: 'Book Club',
  events: [
    createMockEvent({ id: 3, title: 'Session A', start_time: '2026-09-01T18:00:00Z', registration_required: true }),
    createMockEvent({ id: 4, title: 'Session B', start_time: '2026-09-08T18:00:00Z', registration_required: false }),
  ],
}

describe('SeriesEventGroup — a11y', () => {
  it('renders each session as a passive <article> (no fake clickable role)', () => {
    render(
      <SeriesEventGroup group={group} onEventClick={vi.fn()} onRegister={vi.fn()} onRegisterSeries={vi.fn()} />,
    )
    const articles = screen.getAllByRole('article')
    expect(articles).toHaveLength(2)
    articles.forEach((a) => {
      expect(a.tagName).toBe('ARTICLE')
      expect(a).not.toHaveAttribute('tabindex')
    })
  })

  it('navigates via a real title button, not a click handler on the row', async () => {
    const user = userEvent.setup()
    const onEventClick = vi.fn()
    render(
      <SeriesEventGroup group={group} onEventClick={onEventClick} onRegister={vi.fn()} onRegisterSeries={vi.fn()} />,
    )
    await user.click(screen.getByRole('button', { name: 'Week One' }))
    expect(onEventClick).toHaveBeenCalledTimes(1)
  })
})

describe('SeriesEventGroup — register for all sessions', () => {
  it('shows the register-all button when an occurrence takes registration', async () => {
    const user = userEvent.setup()
    const onRegisterSeries = vi.fn()
    render(
      <SeriesEventGroup
        group={regGroup}
        onEventClick={vi.fn()}
        onRegister={vi.fn()}
        onRegisterSeries={onRegisterSeries}
      />,
    )
    await user.click(screen.getByRole('button', { name: /register for all sessions/i }))
    expect(onRegisterSeries).toHaveBeenCalledWith(regGroup)
  })

  it('hides the register-all button for an all-drop-in series', () => {
    render(
      <SeriesEventGroup group={group} onEventClick={vi.fn()} onRegister={vi.fn()} onRegisterSeries={vi.fn()} />,
    )
    expect(screen.queryByRole('button', { name: /register for all sessions/i })).toBeNull()
  })
})
