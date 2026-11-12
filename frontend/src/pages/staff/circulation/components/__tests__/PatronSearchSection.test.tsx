/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeAll, beforeEach, describe, it, expect, vi } from 'vitest'
import { useRef } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PatronSearchSection } from '../PatronSearchSection'
import { usePatronSearch } from '../../hooks/usePatronSearch'
import type { Patron } from '../../types'

vi.mock('@/api/api', () => ({
  searchPatrons: vi.fn(),
}))

vi.mock('@/components/staff/AddPatronModal', () => ({
  default: () => null,
}))

// Bypass the I18n provider tree (which also needs Branding etc.) — t() returns
// a stable accessible label so getByLabelText() can locate the input.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        'staffCirculation.searchPatronsByNameEmail': 'Search patrons by name, email, or card number',
        'staffCirculation.searchByNameEmailOr': 'Search by name, email, or card number',
        'staffCirculation.useArrowsToNavigateEnter': 'Use arrows to navigate, Enter to select',
        'staffCirculation.noPatronsFound': 'No patrons found',
        'staffCirculation.searchFailed': 'Search failed',
        'staffCirculation.registerNewPatron': 'Register new patron',
        'aria.staffCirculation.patronSearchResults': 'Patron search results',
      }
      return map[key] ?? key
    },
  }),
}))

import { searchPatrons } from '@/api/api'

const patrons: Patron[] = [
  { id: 1, first_name: 'Ada', last_name: 'Lovelace', email: 'ada@example.org', is_active: true, library_card: 'L0001', patron_status: 'active' } as Patron,
  { id: 2, first_name: 'Grace', last_name: 'Hopper', email: 'grace@example.org', is_active: true, library_card: 'L0002', patron_status: 'active' } as Patron,
  { id: 3, first_name: 'Edsger', last_name: 'Dijkstra', email: 'edsger@example.org', is_active: true, library_card: 'L0003', patron_status: 'active' } as Patron,
]

function Harness({ onSelect }: { onSelect: (p: Patron) => void }): React.ReactElement {
  const search = usePatronSearch('test-token')
  const inputRef = useRef<HTMLInputElement>(null)
  return (
    <PatronSearchSection
      patronQuery={search.patronQuery}
      setPatronQuery={search.setPatronQuery}
      searchResults={search.searchResults}
      selectedResultIndex={search.selectedResultIndex}
      isSearching={search.isSearching}
      recentPatrons={search.recentPatrons}
      handlePatronSearch={search.handlePatronSearch}
      selectPatron={onSelect}
      handleNavigateUp={search.handleNavigateUp}
      handleNavigateDown={search.handleNavigateDown}
      searchInputRef={inputRef}
    />
  )
}

beforeAll(() => {
  // happy-dom does not implement scrollIntoView
  if (!HTMLElement.prototype.scrollIntoView) {
    HTMLElement.prototype.scrollIntoView = vi.fn()
  }
})

beforeEach(() => {
  vi.mocked(searchPatrons).mockReset()
  vi.mocked(searchPatrons).mockResolvedValue({ patrons, total: patrons.length } as never)
})

describe('PatronSearchSection keyboard navigation', () => {
  it('routes ArrowDown + Enter through the autofocus-aware selectPatron prop', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(<Harness onSelect={onSelect} />)

    const input = screen.getByLabelText(/search patrons by name/i)
    await user.click(input)
    await user.type(input, 'gr')

    // Wait for debounced search (300ms) to resolve and render results
    await waitFor(() => {
      expect(screen.getByText('Grace Hopper')).toBeInTheDocument()
    }, { timeout: 2000 })

    await user.keyboard('{ArrowDown}')
    await user.keyboard('{ArrowDown}')
    await user.keyboard('{Enter}')

    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 2, first_name: 'Grace' }))
  })
})
