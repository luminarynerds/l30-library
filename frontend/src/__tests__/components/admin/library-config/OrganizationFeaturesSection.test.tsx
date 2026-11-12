/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '../../../utils/test-utils'
import { OrganizationFeaturesSection } from '@/components/admin/library-config/OrganizationFeaturesSection'
import { FEATURE_GROUPS } from '@/components/admin/library-config/featureGroups'

vi.mock('focus-trap-react', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock('@/api/organization-features-api', () => ({
  getFeatureRegistry: vi.fn(),
  applyFeaturePreset: vi.fn(),
}))

vi.mock('@/hooks/useOrganizationFeaturesFields', () => ({
  useOrganizationFeaturesFields: (defaults: Record<string, unknown>) => ({
    value: { ...defaults },
    setField: vi.fn(),
    loading: false,
    saving: false,
    save: vi.fn(),
    refresh: vi.fn(),
  }),
}))

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}))

import { getFeatureRegistry } from '@/api/organization-features-api'
const mockedGetFeatureRegistry = vi.mocked(getFeatureRegistry)

function registryFrom(keys: string[]) {
  return keys.map((key) => ({ key, label: key }))
}

const ALL_GROUPED_KEYS = FEATURE_GROUPS.flatMap((g) => g.toggles.map((t) => t.key))

describe('OrganizationFeaturesSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders a section per group when the registry covers every known key', async () => {
    mockedGetFeatureRegistry.mockResolvedValue(registryFrom(ALL_GROUPED_KEYS))
    render(<OrganizationFeaturesSection onBack={() => {}} />)
    for (const group of FEATURE_GROUPS) {
      await waitFor(() => expect(screen.getByText(group.title)).toBeInTheDocument())
    }
  })

  it('renders a toggle row per registry entry, plus an Other card for unmapped keys', async () => {
    mockedGetFeatureRegistry.mockResolvedValue([
      ...registryFrom(ALL_GROUPED_KEYS),
      { key: 'experimental_widget_enabled', label: 'experimental_widget_enabled' },
    ])
    render(<OrganizationFeaturesSection onBack={() => {}} />)
    await waitFor(() => expect(screen.getByText('Other')).toBeInTheDocument())
    expect(screen.getByText('experimental_widget_enabled')).toBeInTheDocument()
  })

  it('skips groups whose toggles are not in the registry', async () => {
    const onlyOneKey = ['patron_portal_enabled']
    mockedGetFeatureRegistry.mockResolvedValue(registryFrom(onlyOneKey))
    render(<OrganizationFeaturesSection onBack={() => {}} />)
    await waitFor(() => expect(screen.getByText('Patron Experience')).toBeInTheDocument())
    expect(screen.queryByText('Advanced')).not.toBeInTheDocument()
    expect(screen.queryByText('Operations')).not.toBeInTheDocument()
  })
})
