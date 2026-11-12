/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import type { HubCategory } from '../../components/navigation/NavigationHub'
import AdminSettingsHubPage from '../AdminSettingsHubPage'

// i18n: return the key so we can assert on stable identifiers.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}))

// Render NavigationHub as a flat list of every item path it receives, so the
// test sees exactly which links survived the feature filter.
vi.mock('../../components/navigation/NavigationHub', () => ({
  default: ({ categories }: { categories: HubCategory[] }) => (
    <ul>
      {categories.flatMap((c) =>
        c.items.map((i) => (
          <li key={`${c.id}:${i.to}`} data-testid="hub-item">
            {i.to}
          </li>
        )),
      )}
    </ul>
  ),
}))

vi.mock('../../components/navigation/HubShortcutsRail', () => ({
  default: () => null,
}))
vi.mock('../../components/navigation/hubVisits', () => ({
  logHubVisit: vi.fn(),
}))

const mockIsFeatureEnabled = vi.fn()
vi.mock('../../contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({ isFeatureEnabled: mockIsFeatureEnabled }),
}))

function paths() {
  return screen.getAllByTestId('hub-item').map((el) => el.textContent)
}

describe('AdminSettingsHubPage feature gating', () => {
  it('hides links whose feature is off and keeps ungated links', () => {
    mockIsFeatureEnabled.mockImplementation(
      (f: string) => f !== 'ai_tools_enabled' && f !== 'learning_platform_enabled',
    )

    render(<AdminSettingsHubPage />)
    const shown = paths()

    // Gated + off -> hidden
    expect(shown).not.toContain('/staff/admin/ai')
    expect(shown).not.toContain('/staff/admin/courses')
    expect(shown).not.toContain('/staff/admin/learning-paths')
    // Ungated -> always shown
    expect(shown).toContain('/staff/admin/circulation-policy')
    expect(shown).toContain('/staff/admin/users')
    // Gated but on -> shown
    expect(shown).toContain('/staff/admin/events')
  })

  it('shows every gated link when all features are on', () => {
    mockIsFeatureEnabled.mockReturnValue(true)

    render(<AdminSettingsHubPage />)
    const shown = paths()

    expect(shown).toContain('/staff/admin/ai')
    expect(shown).toContain('/staff/admin/courses')
    expect(shown).toContain('/staff/admin/legal')
  })
})
