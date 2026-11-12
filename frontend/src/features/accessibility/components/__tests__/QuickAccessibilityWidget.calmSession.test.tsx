/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { useState } from 'react'
import { render, waitFor } from '@testing-library/react'
import { screen } from '@testing-library/dom'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'

// Mock i18n so neither the widget nor UnifiedAccessibilityProvider's useI18nSync
// needs the full I18nProvider/BrandingProvider tree.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (_k: string, fb?: string) => fb ?? _k, setLanguage: () => {}, language: 'en', isRTL: false }),
  useLanguage: () => ({ language: 'en', setLanguage: () => {}, isRTL: false }),
  t: (_k: string, fb?: string) => fb ?? _k,
}))
vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({ t: (_k: string, fb?: string) => fb ?? _k, setLanguage: () => {}, language: 'en', isRTL: false }),
  useLanguage: () => ({ language: 'en', setLanguage: () => {}, isRTL: false }),
}))

import { MemoryRouter } from 'react-router-dom'

import { UnifiedAccessibilityProvider } from '../../context/UnifiedAccessibilityContext'
import { useUnifiedAccessibility } from '../../hooks/useUnifiedAccessibility'
import { LOW_ANXIETY_PRESET } from '../../config/presets.config'
import { QuickAccessibilityWidget } from '../QuickAccessibilityWidget'

function SettingsProbe() {
  const { settings } = useUnifiedAccessibility()
  return (
    <div
      data-testid="probe"
      data-reduce-motion={String(settings.reduceMotion)}
      data-muted-colors={String(settings.mutedColors)}
      data-quiet-mode={String(settings.quietMode)}
    />
  )
}

function ControlledHarness() {
  const [open, setOpen] = useState(false)
  return (
    <MemoryRouter>
      <UnifiedAccessibilityProvider>
        <button type="button" onClick={() => setOpen(true)}>
          open a11y
        </button>
        <SettingsProbe />
        <QuickAccessibilityWidget open={open} onOpenChange={setOpen} showCalmSession />
      </UnifiedAccessibilityProvider>
    </MemoryRouter>
  )
}

describe('QuickAccessibilityWidget controlled mode + Calm work session', () => {
  it('renders no floating launcher button when controlled and closed', () => {
    render(<ControlledHarness />)
    expect(
      screen.queryByRole('button', { name: /open accessibility quick settings/i }),
    ).not.toBeInTheDocument()
  })

  it('opens the panel when the controlling host sets open=true', async () => {
    const user = userEvent.setup()
    render(<ControlledHarness />)
    await user.click(screen.getByRole('button', { name: /open a11y/i }))
    expect(await screen.findByRole('dialog')).toBeInTheDocument()
  })

  it('Calm work session applies the Calm Mode preset settings', async () => {
    const user = userEvent.setup()
    render(<ControlledHarness />)
    await user.click(screen.getByRole('button', { name: /open a11y/i }))
    const calmBtn = await screen.findByRole('button', { name: /calm work session/i })
    await user.click(calmBtn)
    const probe = screen.getByTestId('probe')
    await waitFor(() => {
      // These three are the core ND keys named in the task; assert they match
      // the existing preset rather than hand-rolled values.
      expect(probe.getAttribute('data-reduce-motion')).toBe(
        String(LOW_ANXIETY_PRESET.settings.reduceMotion),
      )
      expect(probe.getAttribute('data-muted-colors')).toBe(
        String(LOW_ANXIETY_PRESET.settings.mutedColors),
      )
      expect(probe.getAttribute('data-quiet-mode')).toBe(
        String(LOW_ANXIETY_PRESET.settings.quietMode),
      )
    })
  })
})
