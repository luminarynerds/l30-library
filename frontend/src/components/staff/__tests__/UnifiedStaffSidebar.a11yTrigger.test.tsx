/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render } from '@testing-library/react'
import { screen } from '@testing-library/dom'
import userEvent from '@testing-library/user-event'
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
})

describe('UnifiedStaffSidebar accessibility trigger', () => {
  it('renders an Accessibility settings button when onOpenAccessibility is provided', () => {
    setRole('staff')
    render(
      <MemoryRouter initialEntries={['/staff']}>
        <UnifiedStaffSidebar onOpenAccessibility={() => {}} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: /accessibility settings/i })).toBeInTheDocument()
  })

  it('calls onOpenAccessibility when the trigger is activated', async () => {
    const user = userEvent.setup()
    const onOpen = vi.fn()
    setRole('staff')
    render(
      <MemoryRouter initialEntries={['/staff']}>
        <UnifiedStaffSidebar onOpenAccessibility={onOpen} />
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { name: /accessibility settings/i }))
    expect(onOpen).toHaveBeenCalledTimes(1)
  })

  it('omits the trigger when no handler is provided', () => {
    setRole('staff')
    render(
      <MemoryRouter initialEntries={['/staff']}>
        <UnifiedStaffSidebar />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('button', { name: /accessibility settings/i })).not.toBeInTheDocument()
  })
})
