/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render } from "@testing-library/react"
import { screen, waitFor } from "@testing-library/react"
import userEvent from '@testing-library/user-event'

// Mock BrandingContext before importing anything that uses it (I18nProvider does).
vi.mock('@/contexts/BrandingContext', () => ({
  useBrandingContext: () => ({
    branding: {
      library_name: 'Test Library',
      library_short_name: 'TL',
      domain: 'test.lib',
      contact_email: 'a@b',
      privacy_email: 'a@b',
      indie_email: 'a@b',
      giving_email: 'a@b',
      events_email: 'a@b',
      print_email: 'a@b',
      makerspace_email: 'a@b',
      phone: '555-0100',
      address_line1: '1 Main St',
      address_line2: 'City, ST 00000',
      city: 'City',
      state: 'ST',
      zip_code: '00000',
      primary_color: '#000',
      accent_color: '#000',
      card_prefix: 'TL',
      product_name: 'Test',
      product_tagline: '',
      hero_title: '',
      hero_subtitle: '',
      tagline: '',
    },
    loading: false,
    setupComplete: true,
    hasAdmin: true,
    refresh: vi.fn(),
  }),
  BrandingProvider: ({ children }: { children: React.ReactNode }) => children,
}))

import { I18nProvider } from '../../i18n/I18nContext'
import LanguageSwitcher from '../LanguageSwitcher'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString()
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

describe('LanguageSwitcher', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.lang = 'en'
  })

  const setup = () => {
    const user = userEvent.setup()
    render(
      <I18nProvider>
        <LanguageSwitcher />
      </I18nProvider>,
    )
    return { user, button: screen.getByRole('button', { expanded: false }) }
  }

  it('renders language icon button', () => {
    setup()
    expect(screen.getByRole('button', { expanded: false })).toBeInTheDocument()
  })

  it('opens language dropdown on button click', async () => {
    const { user, button } = setup()
    await user.click(button)

    await waitFor(() => {
      expect(button).toHaveAttribute('aria-expanded', 'true')
    })
  })

  it('displays all language options in dropdown', async () => {
    const { user, button } = setup()
    await user.click(button)

    const menu = await screen.findByRole('menu')
    expect(menu).toBeInTheDocument()
    // L30 currently ships 2 supported languages (en, es) — see src/i18n/translations.ts
    const items = screen.getAllByRole('menuitemradio')
    expect(items.length).toBeGreaterThanOrEqual(2)
  })

  it('marks the current language with aria-checked', async () => {
    const { user, button } = setup()
    await user.click(button)

    await screen.findByRole('menu')
    const items = screen.getAllByRole('menuitemradio')
    const english = items.find((el) => el.textContent?.includes('English'))
    expect(english).toHaveAttribute('aria-checked', 'true')
  })

  it('changes language to Spanish without page reload', async () => {
    const { user, button } = setup()
    await user.click(button)

    const spanish = await screen.findByRole('menuitemradio', { name: /Español/ })
    await user.click(spanish)

    expect(localStorage.getItem('lsc-language-preference')).toBe('es')
    expect(document.documentElement.lang).toBe('es')
  })

  it('closes dropdown after language selection', async () => {
    const { user, button } = setup()
    await user.click(button)

    await waitFor(() => expect(button).toHaveAttribute('aria-expanded', 'true'))

    const spanish = await screen.findByRole('menuitemradio', { name: /Español/ })
    await user.click(spanish)

    await waitFor(() => expect(button).toHaveAttribute('aria-expanded', 'false'))
  })

  it('persists language selection to localStorage', async () => {
    const { user, button } = setup()
    await user.click(button)

    const spanish = await screen.findByRole('menuitemradio', { name: /Español/ })
    await user.click(spanish)

    expect(localStorage.getItem('lsc-language-preference')).toBe('es')
  })

  it('closes dropdown when pressing Escape', async () => {
    const { user, button } = setup()
    await user.click(button)

    await waitFor(() => expect(button).toHaveAttribute('aria-expanded', 'true'))

    await user.keyboard('{Escape}')

    await waitFor(() => expect(button).toHaveAttribute('aria-expanded', 'false'))
  })
})
