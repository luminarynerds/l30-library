/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { screen } from '@testing-library/dom'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/contexts/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({
    features: {}, loading: false, isFeatureEnabled: () => true, fetchFeatures: vi.fn(),
  }),
}))
vi.mock('@/hooks/usePendingFlagCount', () => ({ usePendingFlagCount: () => 0 }))
vi.mock('@/hooks/useAllHubFavorites', () => ({ useAllHubFavorites: vi.fn(() => ({ favoritePaths: [], isLoading: false })) }))

import { useAuth } from '@/contexts/AuthContext'
import { useAllHubFavorites } from '@/hooks/useAllHubFavorites'
import { clearUIStateCache } from '@/hooks/usePersistedState'
import { UnifiedStaffSidebar } from '../UnifiedStaffSidebar'

const setUser = (role: string, is_board_member = false) => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: 1, role, is_board_member } as any,
    token: 't', isLoading: false, isAuthenticated: true,
  } as any)
}

const store = new Map<string, string>()
beforeEach(() => {
  store.clear(); clearUIStateCache()
  vi.mocked(useAllHubFavorites).mockReturnValue({ favoritePaths: [], isLoading: false })
  vi.mocked(localStorage.getItem).mockImplementation((k) => store.get(k) ?? null)
  vi.mocked(localStorage.setItem).mockImplementation((k, v) => { store.set(k, v) })
  vi.mocked(localStorage.removeItem).mockImplementation((k) => { store.delete(k) })
})

const renderAt = (path = '/staff') => render(
  <MemoryRouter initialEntries={[path]}><UnifiedStaffSidebar /></MemoryRouter>,
)

describe('UnifiedStaffSidebar — lean rail', () => {
  it('renders the four default areas for plain staff', async () => {
    setUser('staff')
    const { container } = renderAt()
    await waitFor(() => {
      for (const p of ['/staff/front-desk-hub','/staff/collection-hub','/staff/library-hub','/staff/report-hub']) {
        expect(container.querySelector(`a[href="${p}"]`)).toBeTruthy()
      }
    })
  })

  it('hides Board and Admin from plain staff', () => {
    setUser('staff')
    const { container } = renderAt()
    expect(container.querySelector('a[href="/staff/board-hub"]')).toBeNull()
    expect(container.querySelector('a[href="/staff/admin/settings"]')).toBeNull()
  })

  it('shows Board for a board member and Admin for a director', () => {
    setUser('staff', true)
    const board = renderAt()
    expect(board.container.querySelector('a[href="/staff/board-hub"]')).toBeTruthy()
    board.unmount()
    setUser('director')
    const dir = renderAt()
    expect(dir.container.querySelector('a[href="/staff/admin/settings"]')).toBeTruthy()
  })

  it('renders no in-rail search box', () => {
    setUser('staff')
    renderAt()
    expect(screen.queryByPlaceholderText(/find a page/i)).toBeNull()
    expect(screen.queryByRole('textbox')).toBeNull()
  })

  it('shows the Favorites section with the user\'s starred items', async () => {
    setUser('staff')
    vi.mocked(useAllHubFavorites).mockReturnValue({ favoritePaths: ['/staff/cataloging'], isLoading: false })
    const { container } = renderAt()
    await waitFor(() => {
      expect(screen.getByText(/favorites/i)).toBeInTheDocument()
      expect(container.querySelector('a[href="/staff/cataloging"]')).toBeTruthy()
    })
  })

  it('omits the Favorites section when there are none', () => {
    setUser('staff')
    vi.mocked(useAllHubFavorites).mockReturnValue({ favoritePaths: [], isLoading: false })
    renderAt()
    expect(screen.queryByText(/favorites/i)).toBeNull()
  })

  it('labels the navigation landmark "Staff" for screen readers', () => {
    setUser('staff')
    renderAt()
    expect(screen.getByRole('navigation', { name: /staff/i })).toBeInTheDocument()
  })
})
