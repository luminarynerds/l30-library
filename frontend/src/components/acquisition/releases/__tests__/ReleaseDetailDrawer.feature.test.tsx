/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ReleaseDetailDrawer from '../ReleaseDetailDrawer'
import type { LibrarianRelease } from '../types'

vi.mock('@/i18n', () => ({
  getCurrentLocale: () => 'en-US',
  useTranslation: () => ({ t: (_k: string, f?: string) => f ?? _k }),
}))

function makeRelease(overrides: Partial<LibrarianRelease['book']> = {}): LibrarianRelease {
  return {
    book: {
      id: 'book-1',
      title: 'Test Title',
      author_id: 'author-1',
      author_name: 'Test Author',
      release_date: '2026-09-01',
      is_date_exact: true,
      isbn_13: '9781234567890',
      age_rating: 'adult',
      cover_url: null,
      list_price: 28.0,
      status: 'upcoming',
      source: 'editorial_rss',
      is_featured: false,
      ...overrides,
    },
    author_name: 'Test Author',
    library_status: 'new',
    demand_score: 0,
    catalog_item_id: null,
  }
}

describe('ReleaseDetailDrawer feature button', () => {
  it('calls onFeature when the Feature button is clicked', async () => {
    const onFeature = vi.fn()
    render(
      <ReleaseDetailDrawer
        release={makeRelease()}
        onClose={() => {}}
        onAddToPO={() => {}}
        onFeature={onFeature}
        formatMoney={(n) => `$${n.toFixed(2)}`}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /feature/i }))
    expect(onFeature).toHaveBeenCalledTimes(1)
  })

  it('shows "Feature" when the title is not yet featured', () => {
    render(
      <ReleaseDetailDrawer
        release={makeRelease({ is_featured: false })}
        onClose={() => {}}
        onAddToPO={() => {}}
        onFeature={() => {}}
        formatMoney={(n) => `$${n.toFixed(2)}`}
      />,
    )

    expect(screen.getByRole('button', { name: /feature this title/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /unfeature/i })).not.toBeInTheDocument()
  })

  it('shows "Unfeature" when the title is already featured', () => {
    render(
      <ReleaseDetailDrawer
        release={makeRelease({ is_featured: true })}
        onClose={() => {}}
        onAddToPO={() => {}}
        onFeature={() => {}}
        formatMoney={(n) => `$${n.toFixed(2)}`}
      />,
    )

    expect(screen.getByRole('button', { name: /unfeature/i })).toBeInTheDocument()
  })
})
