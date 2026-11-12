/// <reference types="@testing-library/jest-dom" />
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Read-alikes section on the item detail page: renders recommendation
 * cards linking to each item, and renders nothing at all (no skeleton,
 * no error banner) when there are no recommendations.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '../../../../__tests__/utils/test-utils'
import { ReadAlikes } from '../ReadAlikes'
import type { ItemRecommendation } from '@/api/api'

function makeRec(overrides: Partial<ItemRecommendation> = {}): ItemRecommendation {
  return {
    id: 7,
    title: 'The Lager Queen of Minnesota',
    author: 'J. Ryan Stradal',
    is_pinned: false,
    cover_image: null,
    available: true,
    ...overrides,
  }
}

describe('ReadAlikes', () => {
  it('renders a card per recommendation linking to the item', () => {
    render(
      <ReadAlikes
        items={[
          makeRec(),
          makeRec({ id: 8, title: 'Kitchens of the Great Midwest', available: false }),
        ]}
      />
    )

    // Title also renders on the text-based placeholder cover tile.
    expect(screen.getAllByText('The Lager Queen of Minnesota').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Kitchens of the Great Midwest').length).toBeGreaterThan(0)
    const links = screen.getAllByRole('link')
    expect(links.map((l) => l.getAttribute('href'))).toEqual(['/catalog/7', '/catalog/8'])
  })

  it('renders nothing when there are no recommendations', () => {
    render(<ReadAlikes items={[]} />)
    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.queryByRole('heading')).toBeNull()
  })
})
