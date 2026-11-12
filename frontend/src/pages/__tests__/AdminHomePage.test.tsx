/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Smoke tests for the home-page admin UI:
 *   - tab navigation renders the right editor
 *   - hero list calls listHeroPicks and shows item title
 *   - shelf list calls listShelves and shows heading
 *   - page config editor loads + saves
 *   - hero editor validation surfaces (item required)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

const mocks = vi.hoisted(() => ({
  listHeroPicks: vi.fn(),
  createHeroPick: vi.fn(),
  updateHeroPick: vi.fn(),
  deleteHeroPick: vi.fn(),
  listShelves: vi.fn(),
  createShelf: vi.fn(),
  updateShelf: vi.fn(),
  deleteShelf: vi.fn(),
  getHomeConfig: vi.fn(),
  updateHomeConfig: vi.fn(),
  searchCatalogForPicker: vi.fn(),
}))

vi.mock('@/api/home', () => ({
  ...mocks,
  HOME_SHELF_QUERY_KINDS: [
    'new_arrivals',
    'staff_picks',
    'subject',
    'format',
    'circulation_top',
    'manual_list',
  ],
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  __esModule: true,
}))

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (_: string, fallback?: string) => fallback ?? _,
    language: 'en',
    isRTL: false,
    setLanguage: vi.fn(),
  }),
}))

// AdminShell pulls in StaffLayout → mock so we don't drag the whole shell graph.
vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}))

import AdminHomePage from '../AdminHomePage'

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.listHeroPicks.mockResolvedValue([
    {
      id: 1,
      item: { id: 10, title: 'Test Book', author: 'A. Writer', item_type: 'book' },
      annotation_md: 'A great read.',
      cta_label: 'Borrow',
      cta_href: null,
      active_from: new Date(Date.now() - 86_400_000).toISOString(),
      active_to: null,
    },
  ])
  mocks.listShelves.mockResolvedValue([
    {
      id: 1,
      slug: 'new-stuff',
      heading: 'New This Week',
      description: '',
      query_kind: 'new_arrivals',
      query_params: { since_days: 7 },
      sort_order: 0,
      is_active: true,
      max_items: 6,
      view_all_href: null,
      updated_at: new Date().toISOString(),
    },
  ])
  mocks.getHomeConfig.mockResolvedValue({
    eyebrow: 'Welcome',
    hero_visible: true,
    picks_link_label: null,
    picks_link_href: null,
    empty_state_message: null,
  })
  mocks.updateHomeConfig.mockResolvedValue({
    eyebrow: 'Welcome back',
    hero_visible: true,
    picks_link_label: null,
    picks_link_href: null,
    empty_state_message: null,
  })
})

describe('AdminHomePage', () => {
  it('renders Hero tab by default and lists hero picks', async () => {
    wrap(<AdminHomePage />)
    await waitFor(() => expect(mocks.listHeroPicks).toHaveBeenCalled())
    expect(await screen.findByText('Test Book')).toBeInTheDocument()
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('switches to the Shelves tab and lists shelves', async () => {
    wrap(<AdminHomePage />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('tab', { name: /Shelves/i }))
    await waitFor(() => expect(mocks.listShelves).toHaveBeenCalled())
    expect(await screen.findByText('New This Week')).toBeInTheDocument()
  })

  it('Page tab loads config and saves it', async () => {
    wrap(<AdminHomePage />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('tab', { name: /Page/i }))
    await waitFor(() => expect(mocks.getHomeConfig).toHaveBeenCalled())
    const input = (await screen.findByLabelText(/Eyebrow text/i)) as HTMLInputElement
    expect(input.value).toBe('Welcome')
    await user.clear(input)
    await user.type(input, 'Welcome back')
    await user.click(screen.getByRole('button', { name: /^Save$/i }))
    await waitFor(() => expect(mocks.updateHomeConfig).toHaveBeenCalled())
    expect(mocks.updateHomeConfig.mock.calls[0]?.[0]).toMatchObject({ eyebrow: 'Welcome back' })
  })

  it('Hero editor blocks save without an item', async () => {
    wrap(<AdminHomePage />)
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: /New hero pick/i }))
    // Required CTA + active_from to pass HTML validation; then attempt save → mutationFn rejects.
    await user.type(screen.getByLabelText(/CTA label/i), 'Borrow')
    await user.type(screen.getByLabelText(/Active from/i), '2026-06-01T09:00')
    await user.click(screen.getByRole('button', { name: /^Save$/i }))
    await waitFor(() => {
      expect(mocks.createHeroPick).not.toHaveBeenCalled()
    })
  })
})
