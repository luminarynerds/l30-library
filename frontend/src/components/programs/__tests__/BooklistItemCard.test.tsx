/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BooklistItemCard from '../BooklistItemCard'
import type { ProgramBooklistItem } from '@/api/domains/content/reading-programs-api'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: { id: 1 } }),
}))

const placeHoldMock = vi.fn(async (..._args: unknown[]) => ({ id: 99 }))
vi.mock('@/api/domains/circulation/circulation-api', () => ({
  placeHold: (token: string, itemId: number) => placeHoldMock(token, itemId),
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))


function makeItem(overrides: Partial<ProgramBooklistItem> = {}): ProgramBooklistItem {
  return {
    id: 1,
    program_id: 5,
    display_order: 0,
    note: null,
    added_at: '2026-05-18T00:00:00Z',
    catalog_item: {
      id: 42,
      title: 'A Wizard of Earthsea',
      author: 'Ursula K. Le Guin',
      cover_url: null,
      status: 'available',
      available_for_hold: true,
    },
    ...overrides,
  }
}

describe('BooklistItemCard', () => {
  it('renders fallback icon when cover_url is null', () => {
    render(<BooklistItemCard item={makeItem()} />)
    expect(screen.getByTestId('booklist-cover-fallback')).toBeInTheDocument()
  })

  it('renders an img when cover_url is set and no fallback', () => {
    render(
      <BooklistItemCard
        item={makeItem({
          catalog_item: {
            id: 7,
            title: 'X',
            author: null,
            cover_url: 'https://example.com/c.jpg',
            status: 'available',
            available_for_hold: true,
          },
        })}
      />,
    )
    expect(screen.queryByTestId('booklist-cover-fallback')).toBeNull()
    expect(screen.getByRole('img')).toHaveAttribute('src', 'https://example.com/c.jpg')
  })

  it('calls placeHold with the catalog_item_id when Place hold is clicked', async () => {
    const user = userEvent.setup()
    render(<BooklistItemCard item={makeItem()} />)
    const btn = screen.getByRole('button', { name: /place hold/i })
    await user.click(btn)
    expect(placeHoldMock).toHaveBeenCalledWith('test-token', 42)
  })

  it('disables Place hold when not available_for_hold', () => {
    render(
      <BooklistItemCard
        item={makeItem({
          catalog_item: {
            id: 42,
            title: 't',
            author: null,
            cover_url: null,
            status: 'checked_out',
            available_for_hold: false,
          },
        })}
      />,
    )
    const btn = screen.getByRole('button', { name: /place hold/i })
    expect(btn).toBeDisabled()
  })
})
