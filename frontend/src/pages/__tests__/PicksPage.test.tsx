/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import PicksPage from '@/pages/PicksPage'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
    language: 'en',
  }),
}))

vi.mock('@/hooks/usePageTitle', () => ({
  usePageTitle: () => undefined,
}))

vi.mock('@/components/HomeBookShelves', () => ({
  default: () => <div data-testid="home-book-shelves">FanShelf content</div>,
}))

describe('PicksPage', () => {
  it('renders the Curated picks heading at h1', () => {
    render(
      <MemoryRouter>
        <PicksPage />
      </MemoryRouter>
    )
    expect(screen.getByRole('heading', { level: 1, name: 'Curated picks' })).toBeInTheDocument()
  })

  it('renders the FanShelf (HomeBookShelves) below the header', async () => {
    render(
      <MemoryRouter>
        <PicksPage />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByTestId('home-book-shelves')).toBeInTheDocument()
    })
  })
})
