/// <reference types="@testing-library/jest-dom" />
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '../../../../__tests__/utils/test-utils'
import CatalogListCard from '../CatalogListCard'
import CatalogGridCard from '../CatalogGridCard'
import type { CatalogItem } from '@/api/api'
import type { ItemAvailabilityInfo } from '@/hooks/useAvailabilityMap'

const mockItem = (overrides?: Partial<CatalogItem>): CatalogItem => ({
  id: 1,
  title: 'Test Book',
  author: 'Test Author',
  item_type: 'book',
  status: 'checked_out',
  created_at: '2023-01-01T00:00:00Z',
  ...overrides,
} as CatalogItem)

const avail = (total: number, available: number): ItemAvailabilityInfo => ({
  item_id: 1,
  total_copies: total,
  available_copies: available,
  on_loan: total - available,
  status: available > 0 ? 'available' : 'unavailable',
  next_available_date: null,
})

const listCardProps = {
  simplifiedView: false,
  quietMode: false,
  showImages: false,
  isSpeaking: false,
  onSpeak: () => {},
  onStopSpeak: () => {},
}

describe('copy-count availability on result cards', () => {
  describe('CatalogListCard', () => {
    it('shows "X of Y available" for multi-copy titles', () => {
      render(<CatalogListCard item={mockItem()} {...listCardProps} copyAvailability={avail(3, 2)} />)
      // visible line + sr-only status text
      expect(screen.getAllByText(/2 of 3 available/).length).toBeGreaterThan(0)
    })

    it('stays quiet for single-copy titles (no "1 of 1" noise)', () => {
      render(<CatalogListCard item={mockItem()} {...listCardProps} copyAvailability={avail(1, 1)} />)
      expect(screen.queryByText(/1 of 1 available/)).not.toBeInTheDocument()
    })

    it('renders nothing extra when no availability data is provided', () => {
      render(<CatalogListCard item={mockItem()} {...listCardProps} />)
      expect(screen.queryByText(/of \d+ available/)).not.toBeInTheDocument()
    })

    it('hides the visible count in quiet mode (secondary metadata) but keeps it in the accessible name', () => {
      render(
        <CatalogListCard
          item={mockItem()}
          {...listCardProps}
          quietMode={true}
          copyAvailability={avail(3, 2)}
        />,
      )
      const matches = screen.getAllByText(/2 of 3 available/)
      // only the sr-only copy remains
      expect(matches).toHaveLength(1)
      expect(matches[0]!.closest('.sr-only')).not.toBeNull()
    })
  })

  describe('CatalogGridCard', () => {
    it('shows the copy count in the status chip for multi-copy titles', () => {
      render(<CatalogGridCard item={mockItem()} copyAvailability={avail(3, 2)} />)
      // visible badge + sr-only accessible name both carry the unified chip text
      expect(screen.getAllByText(/2 of 3 available/).length).toBeGreaterThan(0)
    })

    it('keeps the plain status chip for single-copy titles (no "1 of 1" noise)', () => {
      render(<CatalogGridCard item={mockItem()} copyAvailability={avail(1, 0)} />)
      expect(screen.queryByText(/0 of 1 available/)).not.toBeInTheDocument()
    })
  })
})
