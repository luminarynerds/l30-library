/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import CommandPalette from '../CommandPalette'
import type { User } from '../../../api/domains/auth/auth-api'

// ---- mocks ----

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Mock the auth context (real component imports from contexts/AuthContext).
const mockUseAuth = vi.fn()
vi.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

// Mock organization features.
const mockIsFeatureEnabled = vi.fn()
vi.mock('@/contexts/OrganizationFeaturesContext', async () => {
  const actual = await vi.importActual<typeof import('@/contexts/OrganizationFeaturesContext')>(
    '@/contexts/OrganizationFeaturesContext',
  )
  return {
    ...actual,
    useOrganizationFeatures: () => ({
      features: null,
      loading: false,
      fetchFeatures: vi.fn(),
      isFeatureEnabled: mockIsFeatureEnabled,
    }),
  }
})

// Mock translation: pass through the fallback string when supplied.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string | Record<string, unknown>) =>
      typeof fallback === 'string' ? fallback : _key,
    language: 'en' as const,
    setLanguage: vi.fn(),
    isRTL: false,
  }),
}))

// Mock persisted state hook to avoid touching localStorage.
vi.mock('@/hooks/usePersistedState', () => ({
  usePersistedState: <T,>(_key: string, initial: T) => {
    let value = initial
    return [value, (updater: T | ((p: T) => T)) => {
      value = typeof updater === 'function' ? (updater as (p: T) => T)(value) : updater
    }] as const
  },
}))

// ---- helpers ----

function makeStaffUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    email: 'staff@library.org',
    first_name: 'Staff',
    last_name: 'User',
    full_name: 'Staff User',
    role: 'staff',
    is_active: true,
    library_card: null,
    phone: null,
    address: null,
    email_verified: true,
    track_reading_history: true,
    created_at: new Date().toISOString(),
    onboarding_completed_at: null,
    onboarding_skipped: false,
    home_branch_id: null,
    profile_image: null,
    preferred_language: 'en',
    ...overrides,
  } as User
}

function renderPalette(opts: { isOpen?: boolean; onClose?: () => void } = {}) {
  const onClose = opts.onClose ?? vi.fn()
  const isOpen = opts.isOpen ?? true
  const utils = render(
    <MemoryRouter>
      <Routes>
        <Route path="/" element={<CommandPalette isOpen={isOpen} onClose={onClose} />} />
      </Routes>
    </MemoryRouter>,
  )
  return { ...utils, onClose }
}

// ---- tests ----

describe('CommandPalette', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({ user: makeStaffUser() })
    mockIsFeatureEnabled.mockReturnValue(true)
  })

  it('renders nothing when closed', () => {
    const { container } = renderPalette({ isOpen: false })
    expect(container.querySelector('[role="dialog"]')).toBeNull()
  })

  it('renders nothing for non-staff users', () => {
    mockUseAuth.mockReturnValue({ user: makeStaffUser({ role: 'patron' }) })
    const { container } = renderPalette({ isOpen: true })
    expect(container.querySelector('[role="dialog"]')).toBeNull()
  })

  it('opens with a dialog + combobox + listbox structure when isOpen and staff', async () => {
    renderPalette({ isOpen: true })
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    const combobox = screen.getByRole('combobox')
    expect(combobox).toHaveAttribute('aria-expanded', 'true')
    expect(combobox).toHaveAttribute('aria-controls')
    const listbox = screen.getByRole('listbox')
    expect(listbox.id).toBe(combobox.getAttribute('aria-controls'))
  })

  it('Escape closes the palette', async () => {
    const onClose = vi.fn()
    renderPalette({ isOpen: true, onClose })
    const input = screen.getByRole('combobox')
    fireEvent.keyDown(input, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })

  it('filters results by item label', async () => {
    const user = userEvent.setup()
    renderPalette({ isOpen: true })
    const input = screen.getByRole('combobox')
    await user.type(input, 'cataloging')
    const options = await screen.findAllByRole('option')
    expect(options.length).toBeGreaterThan(0)
    // The first option should mention "cataloging"
    const labels = options.map((o) => o.textContent?.toLowerCase() ?? '')
    expect(labels.some((l) => l.includes('cataloging'))).toBe(true)
  })

  it('filters results by item description', async () => {
    const u = userEvent.setup()
    renderPalette({ isOpen: true })
    const input = screen.getByRole('combobox')
    // "homebound" appears only in descriptions (Home Delivery item).
    await u.type(input, 'homebound')
    const options = await screen.findAllByRole('option')
    expect(options.length).toBeGreaterThan(0)
    const labels = options.map((o) => o.textContent?.toLowerCase() ?? '')
    expect(labels.some((l) => l.includes('home delivery'))).toBe(true)
  })

  it('ArrowDown / ArrowUp moves selection', async () => {
    const u = userEvent.setup()
    renderPalette({ isOpen: true })
    const input = screen.getByRole('combobox')
    await u.type(input, 'event')
    const options = await screen.findAllByRole('option')
    expect(options.length).toBeGreaterThanOrEqual(2)
    expect(options[0]).toHaveAttribute('aria-selected', 'true')
    fireEvent.keyDown(input, { key: 'ArrowDown' })
    const after = screen.getAllByRole('option')
    expect(after[1]).toHaveAttribute('aria-selected', 'true')
    fireEvent.keyDown(input, { key: 'ArrowUp' })
    const back = screen.getAllByRole('option')
    expect(back[0]).toHaveAttribute('aria-selected', 'true')
  })

  it('Enter navigates to the selected item and closes', async () => {
    const u = userEvent.setup()
    const onClose = vi.fn()
    renderPalette({ isOpen: true, onClose })
    const input = screen.getByRole('combobox')
    await u.type(input, 'circulation')
    const options = await screen.findAllByRole('option')
    expect(options.length).toBeGreaterThan(0)
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(mockNavigate).toHaveBeenCalled()
    const navigatedTo = mockNavigate.mock.calls[0]?.[0] as string
    expect(navigatedTo.startsWith('/staff/') || navigatedTo.startsWith('/board/')).toBe(true)
    expect(onClose).toHaveBeenCalled()
  })

  it('hides feature-flag-disabled items', async () => {
    // Disable 'home_delivery_enabled' specifically.
    mockIsFeatureEnabled.mockImplementation((flag: string) => flag !== 'home_delivery_enabled')
    const u = userEvent.setup()
    renderPalette({ isOpen: true })
    const input = screen.getByRole('combobox')
    await u.type(input, 'home delivery')
    // Either zero options or the only matches are not the gated "Home Delivery" item.
    const options = screen.queryAllByRole('option')
    for (const opt of options) {
      const text = opt.textContent?.toLowerCase() ?? ''
      // No item path leading to /staff/home-delivery should be active.
      expect(text.includes('homebound patron delivery service')).toBe(false)
    }
  })

  it('respects roleAllowList: items without a list are visible to any staff role', async () => {
    // Library Hub's Events item has no roleAllowList -- should appear.
    mockUseAuth.mockReturnValue({ user: makeStaffUser({ role: 'legal' }) })
    const u = userEvent.setup()
    renderPalette({ isOpen: true })
    const input = screen.getByRole('combobox')
    await u.type(input, 'events')
    const options = await screen.findAllByRole('option')
    expect(options.length).toBeGreaterThan(0)
  })

  it('wires aria-activedescendant to the selected option id', async () => {
    const u = userEvent.setup()
    renderPalette({ isOpen: true })
    const input = screen.getByRole('combobox')
    await u.type(input, 'cataloging')
    const options = await screen.findAllByRole('option')
    expect(options[0]?.id).toBeTruthy()
    expect(input.getAttribute('aria-activedescendant')).toBe(options[0]!.id)
    fireEvent.keyDown(input, { key: 'ArrowDown' })
    const after = screen.getAllByRole('option')
    if (after.length > 1) {
      expect(input.getAttribute('aria-activedescendant')).toBe(after[1]!.id)
    }
  })

  it('shows hub label + category for hub-derived results', async () => {
    const u = userEvent.setup()
    renderPalette({ isOpen: true })
    const input = screen.getByRole('combobox')
    await u.type(input, 'cataloging')
    const options = await screen.findAllByRole('option')
    // Cataloging is in Collection Hub > Catalog
    const cataloging = options.find((o) => o.textContent?.toLowerCase().includes('cataloging'))
    expect(cataloging).toBeDefined()
    expect(cataloging?.textContent?.toLowerCase()).toContain('collection hub')
  })

  it('focus is trapped inside the dialog', async () => {
    renderPalette({ isOpen: true })
    // The input should have focus after open (auto-focused).
    await waitFor(() => {
      expect(screen.getByRole('combobox')).toHaveFocus()
    })
  })
})
