/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render } from '../../../../__tests__/utils/test-utils'
import CatalogGridCard from '../CatalogGridCard'
import type { CatalogItem } from '@/api/api'

// Two hooks reach into shared state we don't care about for cover rendering;
// stub them so the card renders deterministically without provider wiring.
vi.mock('@/components/shelf/ShelfBookmark', () => ({
  default: () => null,
}))
vi.mock('@/components/reading-lists/AddToListDropdown', () => ({
  AddToListDropdown: () => null,
}))

const baseItem: CatalogItem = {
  id: 42,
  title: 'The Allowlisted Cover',
  author: 'Test Author',
  item_type: 'book',
  status: 'available',
  isbn: '978-0123456789',
  publisher: 'Test Publisher',
  publication_year: 2024,
  description: 'A test book',
  subjects: 'Test',
  // Anything starting with http(s):// is a CDN URL we MUST NOT render
  // directly in patron-facing surfaces. The card should rewrite this to the
  // backend cover-proxy URL.
  cover_url: 'https://images.unsplash.com/photo-12345?w=400',
  page_count: 300,
  location: 'Main',
  barcode: '1',
  created_at: '2024-01-01T00:00:00Z',
} as unknown as CatalogItem

function renderCard(item: CatalogItem) {
  // `render` from test-utils auto-wraps with MemoryRouter + I18nProvider +
  // QueryClientProvider + accessibility/branding providers so the card's
  // useTranslation() calls work without a per-test provider stack.
  return render(<CatalogGridCard item={item} />)
}

describe('CatalogGridCard cover image', () => {
  it('routes the cover through the backend proxy instead of the third-party CDN', () => {
    const { container } = renderCard(baseItem)
    const img = container.querySelector('img')

    // There IS a rendered <img> (vs. the generative thumbnail).
    expect(img).not.toBeNull()
    // Privacy contract: the rendered src is OUR origin, never a third-party
    // cover CDN like images.unsplash.com / placehold.co / covers.openlibrary.org.
    expect(img!.getAttribute('src')).toBe(`/api/v1/catalog/covers/${baseItem.id}`)
    expect(img!.getAttribute('src')).not.toMatch(/images\.unsplash\.com|placehold\.co|covers\.openlibrary\.org/)
  })

  it('marks the cover image as decorative for assistive tech', () => {
    const { container } = renderCard(baseItem)
    const img = container.querySelector('img')!

    // The surrounding <Link> already carries title + author + status in its
    // aria-label, so the cover image is decorative. Empty alt + aria-hidden
    // removes it from the accessibility tree entirely.
    expect(img.getAttribute('alt')).toBe('')
    expect(img.getAttribute('aria-hidden')).toBe('true')
  })

  it('lazy-loads covers below the fold', () => {
    const { container } = renderCard(baseItem)
    const img = container.querySelector('img')!
    expect(img.getAttribute('loading')).toBe('lazy')
  })

  it('falls back to the generative thumbnail when there is no cover at all', () => {
    const noCover = { ...baseItem, cover_url: null as unknown as string } as CatalogItem
    const { container } = renderCard(noCover)
    // No <img> -> thumbnail rendered (the SVG-icon-based fallback).
    expect(container.querySelector('img')).toBeNull()
  })
})
