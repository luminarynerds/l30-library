/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'

import EventQuickChips from '../EventQuickChips'
import { useEventsFilterUrlSync } from '@/pages/events/hooks/useEventsFilterUrlSync'
import { I18nProvider } from '@/i18n/I18nContext'
import { BrandingProvider } from '@/contexts/BrandingContext'
import type { EventFilters as Filters } from '@/api/api'

function LocationProbe({ onLoc }: { onLoc: (search: string) => void }) {
  const loc = useLocation()
  onLoc(loc.search)
  return null
}

// Mirror the real EventsPageContent wiring: `useEventsFilterUrlSync` owns
// URL <-> filter sync for every param; EventQuickChips only sets filter state.
function HarnessInner({
  initial,
  onLoc,
}: {
  initial: Filters
  onLoc?: (search: string) => void
}) {
  const [filters, setFilters] = useState<Filters>(initial)
  const [showPastEvents, setShowPastEvents] = useState(false)
  useEventsFilterUrlSync({ filters, setFilters, showPastEvents, setShowPastEvents })
  return (
    <>
      <EventQuickChips filters={filters} setFilters={setFilters} />
      {onLoc && <LocationProbe onLoc={onLoc} />}
    </>
  )
}

function Harness({
  initial = {},
  onLoc,
  initialEntries = ['/events'],
}: {
  initial?: Filters
  onLoc?: (search: string) => void
  initialEntries?: string[]
}) {
  return (
    <MemoryRouter initialEntries={initialEntries}>
      <BrandingProvider>
        <I18nProvider>
          <HarnessInner initial={initial} onLoc={onLoc} />
        </I18nProvider>
      </BrandingProvider>
    </MemoryRouter>
  )
}

describe('EventQuickChips', () => {
  it('renders time-window, drop-in, and audience chips', () => {
    render(<Harness />)
    expect(screen.getByRole('button', { name: /^today$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /this weekend/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /next 7 days/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /drop-in only/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /kids/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /seniors/i })).toBeInTheDocument()
  })

  it('toggling Today writes ?when=today and presses the chip', async () => {
    const user = userEvent.setup()
    let lastSearch = ''
    render(<Harness onLoc={(s) => { lastSearch = s }} />)
    const todayBtn = screen.getByRole('button', { name: /^today$/i })
    expect(todayBtn.getAttribute('aria-pressed')).toBe('false')
    await user.click(todayBtn)
    expect(lastSearch).toContain('when=today')
    expect(todayBtn.getAttribute('aria-pressed')).toBe('true')
  })

  it('the time-window chips are single-select — a second pick replaces the first', async () => {
    const user = userEvent.setup()
    let lastSearch = ''
    render(<Harness onLoc={(s) => { lastSearch = s }} />)
    await user.click(screen.getByRole('button', { name: /^today$/i }))
    await user.click(screen.getByRole('button', { name: /this weekend/i }))
    expect(lastSearch).toContain('when=weekend')
    expect(lastSearch).not.toContain('when=today')
    expect(screen.getByRole('button', { name: /^today$/i }).getAttribute('aria-pressed')).toBe('false')
    expect(screen.getByRole('button', { name: /this weekend/i }).getAttribute('aria-pressed')).toBe('true')
  })

  it('re-clicking the active time-window chip clears it', async () => {
    const user = userEvent.setup()
    let lastSearch = ''
    render(<Harness onLoc={(s) => { lastSearch = s }} />)
    const todayBtn = screen.getByRole('button', { name: /^today$/i })
    await user.click(todayBtn)
    await user.click(todayBtn)
    expect(lastSearch).not.toContain('when=')
    expect(todayBtn.getAttribute('aria-pressed')).toBe('false')
  })

  it('drop-in is an independent boolean toggle (?drop_in=1)', async () => {
    const user = userEvent.setup()
    let lastSearch = ''
    render(<Harness onLoc={(s) => { lastSearch = s }} />)
    const dropIn = screen.getByRole('button', { name: /drop-in only/i })
    expect(dropIn.getAttribute('aria-pressed')).toBe('false')
    await user.click(dropIn)
    expect(lastSearch).toContain('drop_in=1')
    expect(dropIn.getAttribute('aria-pressed')).toBe('true')
    await user.click(dropIn)
    expect(lastSearch).not.toContain('drop_in=1')
  })

  it('a time-window pick and a drop-in toggle coexist without clobbering', async () => {
    const user = userEvent.setup()
    let lastSearch = ''
    render(<Harness onLoc={(s) => { lastSearch = s }} />)
    await user.click(screen.getByRole('button', { name: /^today$/i }))
    await user.click(screen.getByRole('button', { name: /drop-in only/i }))
    expect(lastSearch).toContain('when=today')
    expect(lastSearch).toContain('drop_in=1')
  })

  it('audience chips remain multi-select', async () => {
    const user = userEvent.setup()
    let lastSearch = ''
    render(<Harness onLoc={(s) => { lastSearch = s }} />)
    await user.click(screen.getByRole('button', { name: /kids/i }))
    await user.click(screen.getByRole('button', { name: /adults/i }))
    expect(lastSearch).toContain('audiences=kids')
    expect(lastSearch).toContain('audiences=adults')
  })

  it('hydrates when, drop_in, and audiences from the URL on mount', () => {
    render(<Harness initialEntries={['/events?when=weekend&drop_in=1&audiences=teens']} />)
    expect(screen.getByRole('button', { name: /this weekend/i }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: /drop-in only/i }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: /teens/i }).getAttribute('aria-pressed')).toBe('true')
  })

  it('renders always-visible accessibility provision chips', () => {
    render(<Harness />)
    expect(screen.getByRole('button', { name: /sensory-friendly/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^asl$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /captioned/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /step-free/i })).toBeInTheDocument()
  })

  it('accessibility chips are multi-select and write repeated ?accessibility= params', async () => {
    const user = userEvent.setup()
    let lastSearch = ''
    render(<Harness onLoc={(s) => { lastSearch = s }} />)
    await user.click(screen.getByRole('button', { name: /sensory-friendly/i }))
    await user.click(screen.getByRole('button', { name: /^asl$/i }))
    expect(lastSearch).toContain('accessibility=sensory_friendly')
    expect(lastSearch).toContain('accessibility=asl_provided')
    // Re-clicking clears just that one.
    await user.click(screen.getByRole('button', { name: /^asl$/i }))
    expect(lastSearch).not.toContain('accessibility=asl_provided')
    expect(lastSearch).toContain('accessibility=sensory_friendly')
  })

  it('hydrates accessibility provisions from the URL on mount', () => {
    render(<Harness initialEntries={['/events?accessibility=captioning_provided']} />)
    expect(screen.getByRole('button', { name: /captioned/i }).getAttribute('aria-pressed')).toBe('true')
  })
})
