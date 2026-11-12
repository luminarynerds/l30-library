/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import HeroSection from '../HeroSection'

vi.mock('@/contexts/OrganizationFeaturesContext', () => ({ useOrganizationFeatures: () => ({ isFeatureEnabled: () => true }) }))
vi.mock('@/contexts/BrandingContext', () => ({ useBranding: () => ({ hero_title: 'Every <em>chapter</em>.', hero_subtitle: 'Your local library.' }) }))
vi.mock('@/i18n/I18nContext', () => ({ useTranslation: () => ({ t: (key: string, fallback?: string) => fallback ?? key }) }))
vi.mock('@/hooks/useRecentSearches', () => ({ useRecentSearches: () => ({ addRecentSearch: vi.fn(), getFilteredSearches: () => [] }) }))

function Location() { const location = useLocation(); return <output aria-label="destination">{location.pathname}{location.search}</output> }
function setup() { render(<MemoryRouter><HeroSection /><Location /></MemoryRouter>) }

describe('homepage discovery', () => {
  it('uses the tenant subtitle and exposes a stable catalog search label', () => {
    setup()
    expect(screen.getByText('Your local library.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Search catalog' })).toBeInTheDocument()
  })
  it('opens a real large-print filter instead of searching the translated chip label', () => {
    setup()
    fireEvent.click(screen.getByText('Browse by format'))
    fireEvent.click(screen.getByRole('button', { name: 'Large print' }))
    expect(screen.getByLabelText('destination')).toHaveTextContent('/catalog?is_large_print=true')
  })
  it('preserves Enter search and safely encodes the query', () => {
    setup()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: '  A & B  ' } })
    fireEvent.keyDown(screen.getByRole('searchbox'), { key: 'Enter' })
    expect(screen.getByLabelText('destination')).toHaveTextContent('/catalog?q=A%20%26%20B')
  })
})
