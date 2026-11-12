/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import HeroPick from '@/components/home/HeroPick'
import type { HeroPickRead } from '@/api/home'
import { I18nProvider } from '@/i18n/I18nContext'
import { BrandingProvider } from '@/contexts/BrandingContext'

const baseHero: HeroPickRead = {
  id: 1,
  item: { id: 42, title: 'The Test Title', author: 'A. Tester', item_type: 'book' },
  annotation_md: 'A *thoughtful* note about this book.',
  cta_label: 'Place a hold',
  cta_href: null,
  active_from: '2026-05-17T00:00:00Z',
  active_to: null,
}

function renderWithRouter(ui: React.ReactElement) {
  return render(
    <BrandingProvider>
      <I18nProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </I18nProvider>
    </BrandingProvider>,
  )
}

describe('HeroPick', () => {
  it('renders the title as an h2', () => {
    renderWithRouter(<HeroPick hero={baseHero} />)
    const heading = screen.getByRole('heading', { level: 2, name: 'The Test Title' })
    expect(heading).toBeInTheDocument()
  })

  it('renders the markdown annotation (emphasis preserved)', () => {
    renderWithRouter(<HeroPick hero={baseHero} />)
    // ReactMarkdown turns *thoughtful* into <em>thoughtful</em>
    const emphasized = screen.getByText('thoughtful')
    expect(emphasized.tagName).toBe('EM')
  })

  it('falls back to /catalog/<id> when cta_href is empty', () => {
    renderWithRouter(<HeroPick hero={baseHero} />)
    const cta = screen.getByRole('link', { name: 'Place a hold' })
    expect(cta.getAttribute('href')).toBe('/catalog/42')
  })

  it('falls back to a generative thumbnail when the cover image fails', () => {
    renderWithRouter(<HeroPick hero={baseHero} />)
    const img = screen.getByAltText(/The Test Title, by A. Tester, Book cover/)
    fireEvent.error(img)
    expect(screen.queryByAltText(/The Test Title, by A. Tester, Book cover/)).toBeNull()
  })

  it('honors cta_href when provided', () => {
    renderWithRouter(
      <HeroPick hero={{ ...baseHero, cta_href: '/programs/summer-reading' }} />
    )
    const cta = screen.getByRole('link', { name: 'Place a hold' })
    expect(cta.getAttribute('href')).toBe('/programs/summer-reading')
  })
})
