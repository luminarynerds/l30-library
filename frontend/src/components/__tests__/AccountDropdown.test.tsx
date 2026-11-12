/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { axe, toHaveNoViolations } from 'jest-axe'

expect.extend(toHaveNoViolations)

type Role = 'patron' | 'staff' | 'teacher' | 'admin' | 'super_admin' | 'director' | 'legal' | 'bookmobile' | 'homebond'

const mockState = vi.hoisted(() => ({
  auth: {
    isAuthenticated: false as boolean,
    user: null as null | { first_name: string; last_name: string; email: string; role: Role; indie_author?: boolean; is_board_member?: boolean },
    logout: vi.fn(),
  },
  features: {} as Record<string, boolean>,
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockState.auth,
}))
vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({
    isFeatureEnabled: (key: string) => Boolean(mockState.features[key]),
  }),
}))
// I18nContext pulls from BrandingContext during render — stub it.
vi.mock('@/contexts/BrandingContext', () => ({
  useBrandingContext: () => ({
    branding: {
      library_name: 'Test', library_short_name: 'TL', domain: 'test.lib',
      contact_email: 'a@b', privacy_email: 'a@b', indie_email: 'a@b',
      giving_email: 'a@b', events_email: 'a@b', print_email: 'a@b',
      makerspace_email: 'a@b', phone: '555-0100',
      address_line1: '1 Main St', address_line2: 'City, ST 00000',
      city: 'City', state: 'ST', zip_code: '00000',
      primary_color: '#000', accent_color: '#000', card_prefix: 'TL',
      product_name: 'Test', product_tagline: '',
      hero_title: '', hero_subtitle: '', tagline: '',
    },
    loading: false, setupComplete: true, hasAdmin: true, refresh: vi.fn(),
  }),
  BrandingProvider: ({ children }: { children: React.ReactNode }) => children,
}))

import { I18nProvider } from '../../i18n/I18nContext'
import AccountDropdown from '../AccountDropdown'

const renderDropdown = (props: { onOpenLogin?: () => void; onOpenRegister?: () => void } = {}) => {
  const onOpenLogin = props.onOpenLogin ?? vi.fn()
  const onOpenRegister = props.onOpenRegister ?? vi.fn()
  const user = userEvent.setup()
  const utils = render(
    <MemoryRouter>
      <I18nProvider>
        <AccountDropdown onOpenLogin={onOpenLogin} onOpenRegister={onOpenRegister} />
      </I18nProvider>
    </MemoryRouter>,
  )
  return { ...utils, user, onOpenLogin, onOpenRegister }
}

const patronUser = {
  first_name: 'Sam',
  last_name: 'Reader',
  email: 'sam@test.lib',
  role: 'patron' as Role,
}

describe('AccountDropdown', () => {
  // Preload English translations. vitest setup.ts does not preload i18n,
  // and assertions like getByRole('menuitem', { name: /sign in/i }) fail
  // when the rendered DOM still contains raw keys (e.g. navigation.account).

  beforeEach(() => {
    mockState.auth.isAuthenticated = false
    mockState.auth.user = null
    mockState.auth.logout = vi.fn()
    mockState.features = {}
  })

  describe('unauthenticated', () => {
    it('renders an Account trigger button', () => {
      renderDropdown()
      expect(screen.getByRole('button', { expanded: false })).toBeInTheDocument()
    })

    it('opens menu with Login + Register on click', async () => {
      const { user } = renderDropdown()
      await user.click(screen.getByRole('button', { expanded: false }))

      const menu = await screen.findByRole('menu')
      expect(menu).toBeInTheDocument()
      expect(screen.getByRole('menuitem', { name: /sign in/i })).toBeInTheDocument()
      expect(screen.getByRole('menuitem', { name: /register/i })).toBeInTheDocument()
      expect(screen.queryByRole('menuitem', { name: /sign out|logout/i })).not.toBeInTheDocument()
    })

    it('calls onOpenLogin when Login is activated', async () => {
      const { user, onOpenLogin } = renderDropdown()
      await user.click(screen.getByRole('button', { expanded: false }))
      await user.click(await screen.findByRole('menuitem', { name: /sign in/i }))
      expect(onOpenLogin).toHaveBeenCalledTimes(1)
    })

    it('calls onOpenRegister when Register is activated', async () => {
      const { user, onOpenRegister } = renderDropdown()
      await user.click(screen.getByRole('button', { expanded: false }))
      await user.click(await screen.findByRole('menuitem', { name: /register/i }))
      expect(onOpenRegister).toHaveBeenCalledTimes(1)
    })
  })

  describe('authenticated patron', () => {
    beforeEach(() => {
      mockState.auth.isAuthenticated = true
      mockState.auth.user = { ...patronUser }
    })

    it("shows the user's first name on the trigger", () => {
      renderDropdown()
      expect(screen.getByRole('button', { expanded: false })).toHaveTextContent('Sam')
    })

    it('shows My Account and other patron items', async () => {
      const { user } = renderDropdown()
      await user.click(screen.getByRole('button', { expanded: false }))

      await screen.findByRole('menu')
      expect(screen.getByRole('menuitem', { name: /my account/i })).toBeInTheDocument()
      // Canonical "My Checkouts" replaces the old "My Books" pileup; "My Shelf"
      // and "My Ebook Checkouts" now live as tabs inside /account.
      expect(screen.getByRole('menuitem', { name: /my checkouts/i })).toBeInTheDocument()
      expect(screen.queryByRole('menuitem', { name: /^my books$/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('menuitem', { name: /my shelf/i })).not.toBeInTheDocument()
    })

    it('does NOT show Staff or Administration sections', async () => {
      const { user } = renderDropdown()
      await user.click(screen.getByRole('button', { expanded: false }))

      await screen.findByRole('menu')
      expect(screen.queryByRole('menuitem', { name: /^staff$/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('menuitem', { name: /feature flags/i })).not.toBeInTheDocument()
    })

    it('hides My Print Jobs when printing_enabled is false', async () => {
      const { user } = renderDropdown()
      await user.click(screen.getByRole('button', { expanded: false }))

      await screen.findByRole('menu')
      expect(screen.queryByRole('menuitem', { name: /print jobs/i })).not.toBeInTheDocument()
    })

    it('shows My Print Jobs when printing_enabled is true', async () => {
      mockState.features['printing_enabled'] = true
      const { user } = renderDropdown()
      await user.click(screen.getByRole('button', { expanded: false }))

      expect(await screen.findByRole('menuitem', { name: /print jobs/i })).toBeInTheDocument()
    })

    it('calls logout when Sign out is activated', async () => {
      const { user } = renderDropdown()
      await user.click(screen.getByRole('button', { expanded: false }))
      await user.click(await screen.findByRole('menuitem', { name: /sign out|logout/i }))
      expect(mockState.auth.logout).toHaveBeenCalledTimes(1)
    })
  })

  describe('staff user', () => {
    beforeEach(() => {
      mockState.auth.isAuthenticated = true
      mockState.auth.user = { ...patronUser, role: 'staff' }
    })

    it('shows the Staff link but not the old Circulation/Acquisitions shortcuts', async () => {
      const { user } = renderDropdown()
      await user.click(screen.getByRole('button', { expanded: false }))
      await screen.findByRole('menu')

      expect(screen.getByRole('menuitem', { name: /^staff$/i })).toBeInTheDocument()
      expect(screen.queryByRole('menuitem', { name: /circulation/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('menuitem', { name: /acquisitions/i })).not.toBeInTheDocument()
    })
  })

  describe('admin user', () => {
    beforeEach(() => {
      mockState.auth.isAuthenticated = true
      mockState.auth.user = { ...patronUser, role: 'admin' }
    })

    it('shows the Administration section', async () => {
      const { user } = renderDropdown()
      await user.click(screen.getByRole('button', { expanded: false }))
      await screen.findByRole('menu')

      expect(screen.getByRole('menuitem', { name: /feature flags/i })).toBeInTheDocument()
      expect(screen.getByRole('menuitem', { name: /site settings/i })).toBeInTheDocument()
    })
  })

  describe('accessibility toggles moved out', () => {
    beforeEach(() => {
      mockState.auth.isAuthenticated = true
      mockState.auth.user = { ...patronUser }
    })

    it('no longer renders dark mode or calm mode toggles (they live in the accessibility settings)', async () => {
      const { user } = renderDropdown()
      await user.click(screen.getByRole('button', { expanded: false }))
      await screen.findByRole('menu')

      expect(screen.queryByRole('menuitemcheckbox', { name: /dark mode/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('menuitemcheckbox', { name: /calm mode|full mode/i })).not.toBeInTheDocument()
    })
  })

  describe('keyboard + a11y', () => {
    it('closes the menu on Escape and returns focus to the trigger', async () => {
      const { user } = renderDropdown()
      const trigger = screen.getByRole('button', { expanded: false })
      await user.click(trigger)
      await screen.findByRole('menu')

      await user.keyboard('{Escape}')
      expect(trigger).toHaveAttribute('aria-expanded', 'false')
      expect(trigger).toHaveFocus()
    })

    it('has no axe violations when open for an authenticated patron', async () => {
      mockState.auth.isAuthenticated = true
      mockState.auth.user = { ...patronUser }
      const { user } = renderDropdown()
      await user.click(screen.getByRole('button', { expanded: false }))
      await screen.findByRole('menu')

      // Scan the full document body since Radix portals content out of `container`.
      // Disabled rules:
      //  - `region`: dropdown is a sub-component, landmarks belong to the parent layout.
      //  - `aria-hidden-focus`: false positive from Radix focus guards in jsdom — Radix
      //    manages focus through these guards correctly in real browsers.
      const results = await axe(document.body, {
        rules: {
          region: { enabled: false },
          'aria-hidden-focus': { enabled: false },
        },
      })
      expect(results).toHaveNoViolations()
    })
  })
})
