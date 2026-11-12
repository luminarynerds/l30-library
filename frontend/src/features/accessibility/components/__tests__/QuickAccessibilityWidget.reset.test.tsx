/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { useState } from 'react'
import { render, waitFor } from '@testing-library/react'
import { screen } from '@testing-library/dom'
import userEvent from '@testing-library/user-event'
import { axe } from 'jest-axe'
import { MemoryRouter } from 'react-router-dom'

// Mock i18n so the widget doesn't need the full I18nProvider/BrandingProvider tree.
// (Language itself lives in I18nContext, not accessibility settings, so reset
// can never touch it — no language assertions needed here.)
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (_k: string, fb?: string) => fb ?? _k, setLanguage: () => {}, language: 'en', isRTL: false }),
  useLanguage: () => ({ language: 'en', setLanguage: () => {}, isRTL: false }),
  t: (_k: string, fb?: string) => fb ?? _k,
}))
vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({ t: (_k: string, fb?: string) => fb ?? _k, setLanguage: () => {}, language: 'en', isRTL: false }),
  useLanguage: () => ({ language: 'en', setLanguage: () => {}, isRTL: false }),
}))

import { UnifiedAccessibilityProvider } from '../../context/UnifiedAccessibilityContext'
import { useUnifiedAccessibility } from '../../hooks/useUnifiedAccessibility'
import { QuickAccessibilityWidget } from '../QuickAccessibilityWidget'

// Seeds a non-default visual setting and one saved profile, then exposes the
// live settings so the test can assert what reset keeps vs clears.
function SeedAndProbe() {
  const { settings, updateSetting } = useUnifiedAccessibility()
  const setLoose = updateSetting as unknown as (k: string, v: unknown) => void
  return (
    <>
      <button type="button" onClick={() => setLoose('reduceMotion', true)}>seed-motion</button>
      <button
        type="button"
        onClick={() =>
          setLoose('savedProfiles', [
            { id: 'p1', name: 'My profile', icon: 'Save', settings: {}, createdAt: '2026-01-01' },
          ])
        }
      >
        seed-profile
      </button>
      <div
        data-testid="probe"
        data-reduce-motion={String(settings.reduceMotion)}
        data-profiles={String((settings.savedProfiles || []).length)}
      />
    </>
  )
}

function Harness() {
  const [open, setOpen] = useState(false)
  return (
    <MemoryRouter>
      <UnifiedAccessibilityProvider>
        <button type="button" onClick={() => setOpen(true)}>open a11y</button>
        <SeedAndProbe />
        <QuickAccessibilityWidget open={open} onOpenChange={setOpen} />
      </UnifiedAccessibilityProvider>
    </MemoryRouter>
  )
}

describe('QuickAccessibilityWidget — Reset to defaults', () => {
  it('clears visual settings but keeps saved profiles', async () => {
    const user = userEvent.setup()
    render(<Harness />)

    await user.click(screen.getByRole('button', { name: /seed-motion/i }))
    await user.click(screen.getByRole('button', { name: /seed-profile/i }))

    const probe = screen.getByTestId('probe')
    await waitFor(() => {
      expect(probe.getAttribute('data-reduce-motion')).toBe('true')
      expect(probe.getAttribute('data-profiles')).toBe('1')
    })

    await user.click(screen.getByRole('button', { name: /open a11y/i }))
    await user.click(await screen.findByRole('button', { name: /^reset to defaults$/i }))
    // Two-step confirm: the destructive "Reset" button only appears after intent.
    await user.click(await screen.findByRole('button', { name: /^reset$/i }))

    await waitFor(() => {
      expect(probe.getAttribute('data-reduce-motion')).toBe('false') // visual setting cleared
      expect(probe.getAttribute('data-profiles')).toBe('1')          // profile preserved
    })
  })

  it('has no axe violations in either reset state', async () => {
    const user = userEvent.setup()
    const { container } = render(<Harness />)
    await user.click(screen.getByRole('button', { name: /open a11y/i }))
    await screen.findByRole('button', { name: /^reset to defaults$/i })
    expect(await axe(container)).toHaveNoViolations()
    // confirm state: destructive button + cancel
    await user.click(screen.getByRole('button', { name: /^reset to defaults$/i }))
    await screen.findByRole('button', { name: /^reset$/i })
    expect(await axe(container)).toHaveNoViolations()
  })

  it('Cancel backs out without changing settings', async () => {
    const user = userEvent.setup()
    render(<Harness />)

    await user.click(screen.getByRole('button', { name: /seed-motion/i }))
    await user.click(screen.getByRole('button', { name: /open a11y/i }))
    await user.click(await screen.findByRole('button', { name: /^reset to defaults$/i }))
    await user.click(await screen.findByRole('button', { name: /^cancel$/i }))

    const probe = screen.getByTestId('probe')
    expect(probe.getAttribute('data-reduce-motion')).toBe('true')
  })
})
