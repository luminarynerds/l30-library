/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/contexts/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({
    features: {}, loading: false, isFeatureEnabled: () => true, fetchFeatures: vi.fn(),
  }),
}))
vi.mock('@/hooks/usePendingFlagCount', () => ({ usePendingFlagCount: () => 0 }))
vi.mock('@/hooks/useAllHubFavorites', () => ({ useAllHubFavorites: () => ({ favoritePaths: [], isLoading: false }) }))

import { useAuth } from '@/contexts/AuthContext'
import { clearUIStateCache } from '@/hooks/usePersistedState'
import { UnifiedStaffSidebar } from '../UnifiedStaffSidebar'

const setRole = (role: string) => {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: 1, role, is_board_member: false } as any,
    token: 't', isLoading: false, isAuthenticated: true,
  } as any)
}

const store = new Map<string, string>()
beforeEach(() => {
  store.clear(); clearUIStateCache()
  vi.mocked(localStorage.getItem).mockImplementation((k) => store.get(k) ?? null)
  vi.mocked(localStorage.setItem).mockImplementation((k, v) => { store.set(k, v) })
  vi.mocked(localStorage.removeItem).mockImplementation((k) => { store.delete(k) })
})

describe('UnifiedStaffSidebar aria-current', () => {
  it('marks the active area link with aria-current="page"', async () => {
    setRole('staff')
    const { container } = render(
      <MemoryRouter initialEntries={['/staff/collection-hub']}>
        <UnifiedStaffSidebar />
      </MemoryRouter>,
    )
    await waitFor(() => {
      const active = Array.from(container.querySelectorAll('a[href="/staff/collection-hub"]'))
      expect(active.length).toBeGreaterThan(0)
      for (const link of active) expect(link).toHaveAttribute('aria-current', 'page')
    })
  })

  it('does not mark inactive area links with aria-current', async () => {
    setRole('staff')
    const { container } = render(
      <MemoryRouter initialEntries={['/staff/collection-hub']}>
        <UnifiedStaffSidebar />
      </MemoryRouter>,
    )
    await waitFor(() => {
      const inactive = Array.from(container.querySelectorAll('a[href="/staff/report-hub"]'))
      expect(inactive.length).toBeGreaterThan(0)
      for (const link of inactive) expect(link).not.toHaveAttribute('aria-current')
    })
  })
})
