/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * The hero eyebrow tagline must honor per-tenant branding (branding.tagline)
 * and only fall back to the shipped i18n default when a tenant has not set one.
 * Regression guard: HeroSection previously rendered t('home.hero.tagline')
 * unconditionally, so a seeded/admin tagline never appeared and every fork
 * showed L30's demo default.
 */
import { vi, describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import HeroSection from '../HeroSection'

vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({ isFeatureEnabled: () => false }),
}))
vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    // No-fallback keys return the key itself, so the i18n default for the
    // tagline surfaces as the literal 'home.hero.tagline'.
    t: (k: string, fallback?: string) => fallback ?? k,
    language: 'en',
  }),
}))

const brandingMock = vi.hoisted(() => ({ value: {} as Record<string, unknown> }))
vi.mock('@/contexts/BrandingContext', () => ({
  useBranding: () => brandingMock.value,
}))

function renderHero() {
  return render(
    <MemoryRouter>
      <HeroSection />
    </MemoryRouter>,
  )
}

describe('HeroSection tagline', () => {
  it('renders the branding tagline when set', () => {
    brandingMock.value = { tagline: 'Serving Orange since 1832.' }
    renderHero()
    expect(screen.getByText('Serving Orange since 1832.')).toBeInTheDocument()
    expect(screen.queryByText('home.hero.tagline')).not.toBeInTheDocument()
  })

  it('falls back to the i18n default when branding tagline is empty', () => {
    brandingMock.value = { tagline: '' }
    renderHero()
    expect(screen.getByText('home.hero.tagline')).toBeInTheDocument()
  })
})
