/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { screen } from '@testing-library/react'
import { vi } from 'vitest'

vi.mock('@/contexts/OrganizationFeaturesContext', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/contexts/OrganizationFeaturesContext')
  return {
    ...actual,
    useOrganizationFeatures: () => ({ isFeatureEnabled: () => true }),
  }
})

vi.mock('@/api/knowledge-base-api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/api/knowledge-base-api')
  return {
    ...actual,
    // Advanced category/type dropdown filters only render once the corpus is
    // large enough to need them (showAdvancedFilters = totalEntryCount > 25,
    // KnowledgeBasePage.tsx, #1517) — small counts here would keep the
    // dropdowns hidden and the comboboxes below unfindable.
    getKnowledgeBaseCategoryCounts: vi.fn().mockResolvedValue({
      categories: { 'Borrowing & Returns': 15, 'Digital Resources': 8, 'Reading Programs': 5 },
      types: { faq: 15, guide: 8, 'read-alike': 5 },
    }),
    getKnowledgeBaseEntries: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    getKnowledgeBaseEntry: vi.fn().mockResolvedValue(null),
    getFAQs: vi.fn().mockResolvedValue([]),
    getReadAlikes: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    markEntryHelpful: vi.fn().mockResolvedValue(undefined),
  }
})

import { render } from '@/__tests__/utils/test-utils'
import KnowledgeBasePage from '@/pages/KnowledgeBasePage'

describe('KnowledgeBasePage filters (phase 1)', () => {
  it('omits categories with zero articles from the dropdown', async () => {
    render(<KnowledgeBasePage />)
    const selects = await screen.findAllByRole('combobox')
    const catSelect = selects[0] as HTMLSelectElement
    await screen.findByRole('option', { name: /Borrowing & Returns|knowledgeBase\.category\.borrowingReturns/i })
    const options = Array.from(catSelect.querySelectorAll('option')).map(o => o.value)
    expect(options).toContain('Borrowing & Returns')
    expect(options).toContain('Digital Resources')
    expect(options).toContain('Reading Programs')
    expect(options).not.toContain('AI Tools')
    expect(options).not.toContain('Indie Catalog')
    expect(options).not.toContain('Account & Membership')
  })

  it('omits types with zero articles from the type dropdown', async () => {
    render(<KnowledgeBasePage />)
    const selects = await screen.findAllByRole('combobox')
    const typeSelect = selects[1] as HTMLSelectElement
    await screen.findByRole('option', { name: /Borrowing & Returns|knowledgeBase\.category\.borrowingReturns/i })
    const options = Array.from(typeSelect.querySelectorAll('option')).map(o => o.value)
    expect(options).toContain('faq')
    expect(options).toContain('guide')
    expect(options).toContain('read-alike')
    expect(options).not.toContain('policy')
    expect(options).not.toContain('how-to')
  })
})


describe('Read-Alike card (phase 1)', () => {
  beforeEach(async () => {
    const api = await import('@/api/knowledge-base-api')
    ;(api.getReadAlikes as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 1,
          if_you_liked: 'Project Hail Mary',
          if_you_liked_author: 'Andy Weir',
          then_try: 'The Kaiju Preservation Society',
          then_try_author: 'John Scalzi',
          reason: 'Both warm, optimistic SF.',
          added_by_name: null,
          created_at: '2026-05-20T00:00:00Z',
          then_try_catalog_id: 42,
          then_try_cover_url: 'https://example.com/kps.jpg',
        },
      ],
      total: 1,
    })
  })

  it('renders a catalog link and cover thumb when catalog_id is present', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<KnowledgeBasePage />)
    await userEvent.click(await screen.findByRole('tab', { name: /read.alikes/i }))
    await userEvent.type(screen.getByPlaceholderText(/book title/i), 'Project')
    const link = await screen.findByRole('link', { name: /The Kaiju Preservation Society/i })
    expect(link).toHaveAttribute('href', '/catalog/42')
    expect(screen.getByRole('img', { name: /Cover of The Kaiju Preservation Society/i }))
      .toHaveAttribute('src', expect.stringContaining('kps.jpg'))
    expect(screen.getByRole('link', { name: /place hold/i })).toBeInTheDocument()
  })

  it('renders plain text + no place-hold button when no catalog match', async () => {
    const api = await import('@/api/knowledge-base-api')
    ;(api.getReadAlikes as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: 2,
          if_you_liked: 'X',
          if_you_liked_author: 'Y',
          then_try: 'Unmatched',
          then_try_author: 'Z',
          reason: '...',
          added_by_name: null,
          created_at: '2026-05-20T00:00:00Z',
          then_try_catalog_id: null,
          then_try_cover_url: null,
        },
      ],
      total: 1,
    })
    const { default: userEvent } = await import('@testing-library/user-event')
    render(<KnowledgeBasePage />)
    await userEvent.click(await screen.findByRole('tab', { name: /read.alikes/i }))
    await userEvent.type(screen.getByPlaceholderText(/book title/i), 'X')
    await screen.findByText('Unmatched')
    expect(screen.queryByRole('link', { name: /^Unmatched$/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /place hold/i })).not.toBeInTheDocument()
  })
})
