/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Regression: PreferencesContext must not strip the accessibility classes that
 * cssApplicator (UnifiedAccessibilityProvider) owns.
 *
 * dyslexia-font / high-contrast / reduce-motion are applied EXCLUSIVELY by
 * cssApplicator from the accessibility-settings store. PreferencesContext used to
 * ALSO toggle them from its own DOM effect, driven by the separate lsc-preferences
 * store (which defaults them all to false) — so on any re-render it turned the
 * user's a11y-widget choices back off, producing a broken, half-applied page.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'

// Anonymous user → no preferences API call.
vi.mock('../AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: false }),
}))
// The single source of truth is cssApplicator; the bridge is a no-op here.
vi.mock('@/features/accessibility/hooks/useAccessibility', () => ({
  useAccessibility: () => ({ updateSetting: vi.fn() }),
}))

import { PreferencesProvider } from '../PreferencesContext'

describe('PreferencesContext does not strip cssApplicator-owned a11y classes', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.className = ''
    document.documentElement.removeAttribute('data-dyslexia-mode')
    document.documentElement.style.fontSize = ''
  })

  it('keeps dyslexia-font / high-contrast / reduce-motion set by the a11y widget', async () => {
    // lsc-preferences (PreferencesContext's store) has everything OFF — the
    // conflicting source that used to win on re-render.
    localStorage.setItem('lsc-preferences', JSON.stringify({
      theme: 'system', font_size: 'medium', focus_mode: 'balanced',
      dyslexia_font: false, high_contrast: false, reduced_motion: false,
    }))

    // Simulate the a11y widget / cssApplicator having already applied the user's choices.
    const root = document.documentElement
    root.classList.add('dyslexia-font', 'high-contrast', 'reduce-motion')
    root.setAttribute('data-dyslexia-mode', 'true')

    render(
      <PreferencesProvider>
        <div />
      </PreferencesProvider>,
    )

    // PreferencesContext's mount effect must leave these alone.
    await waitFor(() => {
      expect(root.classList.contains('dyslexia-font')).toBe(true)
    })
    expect(root.getAttribute('data-dyslexia-mode')).toBe('true')
    expect(root.classList.contains('high-contrast')).toBe(true)
    expect(root.classList.contains('reduce-motion')).toBe(true)
  })
})
