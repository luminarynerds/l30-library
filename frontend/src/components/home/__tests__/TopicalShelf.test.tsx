/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TopicalShelf from '@/components/home/TopicalShelf'
import type { PublicShelfRead } from '@/api/home'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
    language: 'en',
  }),
}))

const shelf: PublicShelfRead = {
  id: 7,
  slug: 'summer-mysteries',
  heading: 'Summer Mysteries',
  description: 'Page-turners for porch reading.',
  view_all_href: '/catalog?shelf=summer-mysteries',
  items: [
    { id: 101, title: 'Mystery One', author: 'Author A', item_type: 'book' },
    { id: 102, title: 'Mystery Two', author: 'Author B', item_type: 'book' },
  ],
}

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('TopicalShelf', () => {
  it('renders the heading at h2 level', () => {
    renderWithRouter(<TopicalShelf shelf={shelf} />)
    const heading = screen.getByRole('heading', { level: 2, name: 'Summer Mysteries' })
    expect(heading).toBeInTheDocument()
  })

  it('renders the description', () => {
    renderWithRouter(<TopicalShelf shelf={shelf} />)
    expect(screen.getByText('Page-turners for porch reading.')).toBeInTheDocument()
  })

  it('renders one link per item with the catalog item URL', () => {
    renderWithRouter(<TopicalShelf shelf={shelf} />)
    const links = screen.getAllByRole('link')
    // 2 item links + 1 see-more
    const itemLinks = links.filter((l) => /^\/catalog\/\d+$/.test(l.getAttribute('href') ?? ''))
    expect(itemLinks).toHaveLength(2)
    expect(itemLinks[0]?.getAttribute('href')).toBe('/catalog/101')
    expect(itemLinks[1]?.getAttribute('href')).toBe('/catalog/102')
  })

  it('falls back to a generative thumbnail when the cover image fails', () => {
    renderWithRouter(<TopicalShelf shelf={shelf} />)
    const img = screen.getByAltText(/Mystery One, by Author A, Book cover/)
    fireEvent.error(img)
    expect(screen.queryByAltText(/Mystery One, by Author A, Book cover/)).toBeNull()
  })

  it('renders covers with descriptive alt text', () => {
    renderWithRouter(<TopicalShelf shelf={shelf} />)
    const img = screen.getByAltText(/Mystery One, by Author A, Book cover/)
    expect(img.getAttribute('src')).toBe('/api/v1/catalog/covers/101')
  })

  it('renders the see-more link when view_all_href is set', () => {
    renderWithRouter(<TopicalShelf shelf={shelf} />)
    const seeMore = screen.getByRole('link', { name: /See more/ })
    expect(seeMore.getAttribute('href')).toBe('/catalog?shelf=summer-mysteries')
  })

  it('omits the see-more link when view_all_href is null', () => {
    renderWithRouter(<TopicalShelf shelf={{ ...shelf, view_all_href: null }} />)
    expect(screen.queryByRole('link', { name: /See more/ })).toBeNull()
  })
})
