/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Catalog card a11y tests — covers Fix 1 (aria-labelledby) and Fix 2 (text
 * floor + always-visible status + solid badge) from the 2026-05-16 audit.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CatalogListCard from '../CatalogListCard'
import CatalogGridCard from '../CatalogGridCard'
import type { CatalogItem } from '@/api/api'

// Stub anything that pulls in providers we don't care about for these
// purely-presentational assertions.
vi.mock('@/components/shelf/ShelfBookmark', () => ({ default: () => null }))
vi.mock('@/components/reading-lists/AddToListDropdown', () => ({
  AddToListDropdown: () => null,
}))
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: null, token: null }),
}))
vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    language: 'en-US',
    t: (key: string, paramsOrFallback?: unknown) =>
      typeof paramsOrFallback === 'string' ? paramsOrFallback : key,
  }),
}))

const baseItem: CatalogItem = {
  id: 7,
  title: 'Braiding Sweetgrass',
  author: 'Robin Wall Kimmerer',
  item_type: 'book',
  status: 'available',
  isbn: '978-1571313560',
  publisher: 'Milkweed',
  publication_year: 2013,
  description: 'Indigenous wisdom and plants.',
  subjects: 'Nature, Indigenous studies',
  cover_url: null,
  page_count: 408,
  location: 'NAT 581.6 KIM',
  barcode: '1',
  call_number: '581.6 KIM',
  content_notes: 'discussion of colonization',
  created_at: '2024-01-01T00:00:00Z',
  lexile_measure: 1100,
} as unknown as CatalogItem

function withProviders(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  )
}

function renderList(item: CatalogItem = baseItem, props: Partial<React.ComponentProps<typeof CatalogListCard>> = {}) {
  return render(
    withProviders(
      <CatalogListCard
        item={item}
        simplifiedView={false}
        quietMode={false}
        showImages={true}
        isSpeaking={false}
        onSpeak={vi.fn()}
        onStopSpeak={vi.fn()}
        {...props}
      />,
    ),
  )
}

function renderGrid(item: CatalogItem = baseItem) {
  return render(withProviders(<CatalogGridCard item={item} />))
}

// ---------------------------------------------------------------------------
// Fix 1 — aria-labelledby
// ---------------------------------------------------------------------------

describe('Fix 1: list card uses aria-labelledby (title + status), not a kitchen-sink aria-label', () => {
  it('accessible name is exactly title + status text — no moods/location/format soup', () => {
    renderList()
    // The link should be findable by title alone, and its accessible name
    // should NOT contain the extra fields. We assert by a strict regex.
    const link = screen.getByRole('link', { name: /Braiding Sweetgrass/i })
    const name = link.getAttribute('aria-label') ?? link.getAttribute('aria-labelledby')
    expect(name).toBeTruthy()
    // Must NOT carry format/LP/moods in the link's accessible name string.
    // We allow author + status; everything else lives in child content.
    const accessibleNameText = (link as HTMLElement).textContent ?? ''
    // The audit problem: the aria-label currently inlines "book" (format).
    // After fix, the link's *aria-label* should be absent (replaced by
    // labelledby) — so getAttribute('aria-label') is null.
    expect(link.getAttribute('aria-label')).toBeNull()
    expect(link.getAttribute('aria-labelledby')).toBeTruthy()
    // The labelledby ids should resolve to elements whose combined text is
    // title (+ optional author) + status. Spot-check that.
    const ids = (link.getAttribute('aria-labelledby') ?? '').split(/\s+/).filter(Boolean)
    const combined = ids
      .map((id) => document.getElementById(id)?.textContent?.trim() ?? '')
      .join(' ')
    expect(combined).toMatch(/Braiding Sweetgrass/)
    expect(combined).toMatch(/Available/i)
    // The kitchen-sink fields are NOT in the name.
    expect(combined).not.toMatch(/large print/i)
    expect(combined).not.toMatch(/content notes/i)
    expect(combined).not.toMatch(/NAT 581/i)
    // The DOM is still wired correctly otherwise.
    expect(accessibleNameText).toContain('Braiding Sweetgrass')
  })
})

describe('Fix 1: grid card uses aria-labelledby (title + status)', () => {
  it('grid card link uses labelledby, not aria-label', () => {
    renderGrid()
    const link = screen.getByRole('link', { name: /Braiding Sweetgrass/i })
    expect(link.getAttribute('aria-label')).toBeNull()
    expect(link.getAttribute('aria-labelledby')).toBeTruthy()
    const ids = (link.getAttribute('aria-labelledby') ?? '').split(/\s+/).filter(Boolean)
    const combined = ids
      .map((id) => document.getElementById(id)?.textContent?.trim() ?? '')
      .join(' ')
    expect(combined).toMatch(/Braiding Sweetgrass/)
    expect(combined).toMatch(/Available/i)
  })
})

// ---------------------------------------------------------------------------
// Fix 2 — text floor at 12px, always-visible status, solid badge
// ---------------------------------------------------------------------------

describe('Fix 2: body micro-text is at least text-xs (12px)', () => {
  it('list card content-notes / location are text-xs, not text-[11px]', () => {
    const { container } = renderList()
    // Find the inner span holding the visible phrase, walk up to its row.
    const contentNotesSpan = Array.from(container.querySelectorAll('span')).find((el) =>
      el.textContent === 'Content notes available',
    ) as HTMLElement | undefined
    expect(contentNotesSpan).toBeDefined()
    const contentNotesRow = contentNotesSpan!.parentElement as HTMLElement
    expect(contentNotesRow.className).not.toMatch(/text-\[11px\]/)
    expect(contentNotesRow.className).toMatch(/text-xs\b/)
    // Location span (carries the call_number/location string), walk up.
    const locSpan = Array.from(container.querySelectorAll('span')).find((el) =>
      el.textContent?.includes('NAT 581.6 KIM'),
    ) as HTMLElement | undefined
    expect(locSpan).toBeDefined()
    const locRow = locSpan!.parentElement as HTMLElement
    expect(locRow.className).not.toMatch(/text-\[11px\]/)
    expect(locRow.className).toMatch(/text-xs\b/)
  })

  it('grid card moods/location are text-xs, not text-[10px]', () => {
    const { container } = renderGrid()
    const moods = Array.from(container.querySelectorAll('*')).find((el) =>
      el.tagName === 'P' && el.textContent?.toLowerCase().includes('nature'),
    ) as HTMLElement | undefined
    if (moods) {
      expect(moods.className).not.toMatch(/text-\[10px\]/)
      expect(moods.className).toMatch(/text-xs\b/)
    }
    const loc = Array.from(container.querySelectorAll('*')).find((el) =>
      el.tagName === 'P' && el.textContent?.includes('NAT 581.6 KIM'),
    ) as HTMLElement | undefined
    expect(loc).toBeDefined()
    expect(loc!.className).not.toMatch(/text-\[10px\]/)
    expect(loc!.className).toMatch(/text-xs\b/)
  })
})

describe('Fix 2: status text always rendered (no color-only status)', () => {
  it('list card renders "Available" text even in quiet mode', () => {
    renderList(baseItem, { quietMode: true })
    // Status text must be in the DOM somewhere (visible or sr-only is fine —
    // but the audit demands visible). Use queryAllByText to allow either.
    const matches = screen.getAllByText(/Available/)
    expect(matches.length).toBeGreaterThan(0)
    // At least one of them should NOT be sr-only (visible status text).
    const visible = matches.find((el) => !el.className.includes('sr-only'))
    expect(visible).toBeDefined()
  })
})

describe('overlay-link pattern: no nested interactive elements', () => {
  const INTERACTIVE = 'a, button, input, select, textarea, [tabindex]'
  const seriesItem = {
    ...baseItem,
    series_name: 'Tales of the Prairie',
    series_number: 2,
  } as unknown as CatalogItem

  it('list card anchors contain no interactive descendants', () => {
    const { container } = renderList(seriesItem)
    const anchors = Array.from(container.querySelectorAll('a'))
    expect(anchors.length).toBeGreaterThan(0)
    for (const a of anchors) {
      expect(a.querySelector(INTERACTIVE)).toBeNull()
    }
    // Buttons (read-aloud etc.) are siblings of the anchor, not descendants.
    for (const btn of Array.from(container.querySelectorAll('button'))) {
      expect(btn.closest('a')).toBeNull()
    }
  })

  it('grid card anchor contains no interactive descendants', () => {
    const { container } = renderGrid()
    const anchors = Array.from(container.querySelectorAll('a'))
    expect(anchors.length).toBeGreaterThan(0)
    for (const a of anchors) {
      expect(a.querySelector(INTERACTIVE)).toBeNull()
    }
    for (const btn of Array.from(container.querySelectorAll('button'))) {
      expect(btn.closest('a')).toBeNull()
    }
  })
})

describe('Fix 2: grid card status badge has solid background (deterministic contrast)', () => {
  it('badge background class does not use /95 opacity', () => {
    const { container } = renderGrid()
    // Find the status badge: a span containing "Available" near absolute positioning.
    const badge = Array.from(container.querySelectorAll('span')).find((el) =>
      el.className.includes('absolute') && el.textContent?.includes('Available'),
    ) as HTMLElement | undefined
    expect(badge).toBeDefined()
    expect(badge!.className).not.toMatch(/\/95\b/)
    // Should still have a status background class (solid).
    expect(badge!.className).toMatch(/bg-status-success-\d{3}/)
  })
})
