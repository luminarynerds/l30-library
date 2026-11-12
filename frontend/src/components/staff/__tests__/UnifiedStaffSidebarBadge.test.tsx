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
vi.mock('@/hooks/useAllHubFavorites', () => ({ useAllHubFavorites: () => ({ favoritePaths: [], isLoading: false }) }))
vi.mock('@/hooks/usePendingFlagCount', () => ({ usePendingFlagCount: () => 3 }))

import { useAuth } from '@/contexts/AuthContext'
import { clearUIStateCache } from '@/hooks/usePersistedState'
import { UnifiedStaffSidebar } from '../UnifiedStaffSidebar'

const store = new Map<string, string>()
beforeEach(() => {
  store.clear(); clearUIStateCache()
  vi.mocked(useAuth).mockReturnValue({
    user: { id: 1, role: 'staff', is_board_member: false } as any,
    token: 't', isLoading: false, isAuthenticated: true,
  } as any)
  vi.mocked(localStorage.getItem).mockImplementation((k) => store.get(k) ?? null)
  vi.mocked(localStorage.setItem).mockImplementation((k, v) => { store.set(k, v) })
  vi.mocked(localStorage.removeItem).mockImplementation((k) => { store.delete(k) })
})

const renderAt = (path = '/staff') => render(
  <MemoryRouter initialEntries={[path]}><UnifiedStaffSidebar /></MemoryRouter>,
)

describe('UnifiedStaffSidebar — pending-flag badge', () => {
  it('renders a pending-flag count on the Help nav link', async () => {
    renderAt()
    await waitFor(() => {
      const helpLink = screen.getByRole('link', { name: /help/i })
      expect(helpLink).toHaveTextContent('3')
    })
  })

  it('the badge has an accessible aria-label naming the count', async () => {
    renderAt()
    await waitFor(() => {
      const badge = screen.getByLabelText(/3 flagged/i)
      expect(badge).toBeTruthy()
    })
  })
})
