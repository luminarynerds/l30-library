/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { useState } from 'react'
import { render, act } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { useEventsFilterUrlSync } from '../useEventsFilterUrlSync'
import type { EventFilters as Filters } from '@/api/api'

type SetFilters = (next: Filters | ((prev: Filters) => Filters)) => void

function Probe({
  onState,
}: {
  onState: (filters: Filters, search: string, setFilters: SetFilters) => void
}) {
  const [filters, setFilters] = useState<Filters>({})
  const [showPastEvents, setShowPastEvents] = useState(false)
  useEventsFilterUrlSync({ filters, setFilters, showPastEvents, setShowPastEvents })
  onState(filters, useLocation().search, setFilters)
  return null
}

function renderHookAt(initialEntries: string[]) {
  let filters: Filters = {}
  let search = ''
  let setFilters: SetFilters = () => {}
  render(
    <MemoryRouter initialEntries={initialEntries}>
      <Probe
        onState={(f, s, sf) => {
          filters = f
          search = s
          setFilters = sf
        }}
      />
    </MemoryRouter>
  )
  return {
    get filters() { return filters },
    get search() { return search },
    setFilters: (next: Filters) => act(() => { setFilters(next) }),
  }
}

describe('useEventsFilterUrlSync — when / drop_in / accessibility', () => {
  it('hydrates accessibility (multi-value) from the URL on mount', () => {
    const h = renderHookAt(['/events?accessibility=wheelchair_accessible&accessibility=asl_provided'])
    expect(h.filters.accessibility).toEqual(['wheelchair_accessible', 'asl_provided'])
  })

  it('hydrates when and drop_in from the URL on mount', () => {
    const h = renderHookAt(['/events?when=today&drop_in=1'])
    expect(h.filters.when).toBe('today')
    expect(h.filters.drop_in).toBe(true)
  })

  it('ignores an out-of-set `when` value from a hand-edited URL', () => {
    const h = renderHookAt(['/events?when=someday'])
    expect(h.filters.when).toBeUndefined()
  })

  it('writes accessibility back to the URL as repeated params', () => {
    const h = renderHookAt(['/events'])
    h.setFilters({ accessibility: ['wheelchair_accessible', 'sensory_friendly'] })
    expect(h.search).toContain('accessibility=wheelchair_accessible')
    expect(h.search).toContain('accessibility=sensory_friendly')
  })

  it('writes when and drop_in back to the URL', () => {
    const h = renderHookAt(['/events'])
    h.setFilters({ when: 'weekend', drop_in: true })
    expect(h.search).toContain('when=weekend')
    expect(h.search).toContain('drop_in=1')
  })

  it('clearing filters drops when / drop_in / accessibility from the URL', () => {
    const h = renderHookAt(['/events?when=today&drop_in=1&accessibility=asl_provided'])
    h.setFilters({})
    expect(h.search).not.toContain('when=')
    expect(h.search).not.toContain('drop_in=')
    expect(h.search).not.toContain('accessibility=')
  })
})
