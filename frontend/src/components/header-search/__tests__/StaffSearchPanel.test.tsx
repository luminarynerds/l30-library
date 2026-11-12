/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for StaffSearchPanel — locks down the staff fan-out search preserved
 * by the HeaderSearch split (PR #753): ranked results across patrons / staff /
 * items / orders / events, the type-filter narrowing, and click-to-route.
 *
 * Why these mocks: StaffSearchPanel calls getAccessToken() and bails when no
 * token is present, so we pre-set the in-memory token. It also fans out to
 * five Promise.allSettled-wrapped APIs, all of which must be mocked.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '../../../__tests__/utils/test-utils'
import { setAccessToken } from '../../../utils/tokenStore'

const mocks = vi.hoisted(() => ({
  searchPatrons: vi.fn(),
  listStaff: vi.fn(),
  searchCatalog: vi.fn(),
  getPurchaseOrders: vi.fn(),
  getEvents: vi.fn(),
  navigate: vi.fn(),
}))

vi.mock('@/api/staff-api', () => ({
  searchPatrons: mocks.searchPatrons,
  listStaff: mocks.listStaff,
}))
vi.mock('../../../api/catalog-api', () => ({
  searchCatalog: mocks.searchCatalog,
}))
vi.mock('../../../api/acquisition-po-api', () => ({
  getPurchaseOrders: mocks.getPurchaseOrders,
}))
vi.mock('@/api/events-api', () => ({
  getEvents: mocks.getEvents,
}))
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mocks.navigate }
})

import StaffSearchPanel from '../StaffSearchPanel'
import type { StaffSearchEntityType } from '../staff-search-utils'

const noop = () => {}

function renderPanel(
  props: Partial<React.ComponentProps<typeof StaffSearchPanel>> = {},
) {
  const defaults: React.ComponentProps<typeof StaffSearchPanel> = {
    query: 'tolkien',
    setQuery: noop,
    isStaffUser: true,
    staffFilter: 'all',
    onClose: noop,
    onClearQuery: noop,
    onConsumeQuery: noop,
    saveRecentSearch: noop,
  }
  return render(
    <MemoryRouter>
      <StaffSearchPanel {...defaults} {...props} />
    </MemoryRouter>,
  )
}

function mockAllSources(query: string) {
  mocks.searchPatrons.mockResolvedValue({
    patrons: [{
      id: 7,
      first_name: 'Tolkien',
      last_name: 'Fan',
      email: 'fan@example.com',
      phone: '555-0100',
      library_card: 'L0007',
    }],
    total: 1, page: 1, per_page: 20,
  })
  mocks.listStaff.mockResolvedValue({
    staff: [{
      id: 3,
      first_name: 'Tolkien',
      last_name: 'Librarian',
      email: 'tlib@example.com',
      department: 'Reference',
      role: 'librarian',
    }],
    total: 1, page: 1, per_page: 25,
  })
  mocks.searchCatalog.mockResolvedValue({
    items: [{
      id: 42,
      title: `Lord of the Rings — ${query}`,
      author: 'Tolkien',
      barcode: 'BC42',
      isbn: '978',
      publisher: 'HM',
      subjects: 'fantasy',
      description: 'an item',
    }],
    total: 1, page: 1, per_page: 25, pages: 1,
  })
  mocks.getPurchaseOrders.mockResolvedValue({
    items: [{
      id: 11,
      po_number: `PO-${query}-1`,
      vendor_name: 'Tolkien Books',
      fund_name: 'Adult Fiction',
      status: 'open',
      total_amount: 100,
    }],
    total: 1, page: 1, per_page: 100,
  })
  mocks.getEvents.mockResolvedValue({
    data: [{
      id: 88,
      title: `Tolkien reading club ${query}`,
      category: 'Book Club',
      location: 'Branch A',
      is_virtual: false,
      description: 'monthly meet-up',
      tags: ['tolkien', 'fantasy'],
    }],
    pagination: { page: 1, per_page: 50, total: 1, total_pages: 1, has_next: false, has_previous: false },
  })
}

beforeEach(() => {
  mocks.searchPatrons.mockReset()
  mocks.listStaff.mockReset()
  mocks.searchCatalog.mockReset()
  mocks.getPurchaseOrders.mockReset()
  mocks.getEvents.mockReset()
  mocks.navigate.mockReset()
  setAccessToken('mock-token')
})

describe('StaffSearchPanel', () => {
  it('renders ranked results from all data sources when staffFilter=all', async () => {
    mockAllSources('tolkien')

    renderPanel({ query: 'tolkien', staffFilter: 'all' })

    expect(await screen.findByText('Tolkien Fan')).toBeInTheDocument()
    expect(screen.getByText('Tolkien Librarian')).toBeInTheDocument()
    expect(screen.getByText(/Lord of the Rings/)).toBeInTheDocument()
    expect(screen.getByText('PO-tolkien-1')).toBeInTheDocument()
    expect(screen.getByText(/Tolkien reading club/)).toBeInTheDocument()
  })

  it('narrows results to patrons only when staffFilter=patron', async () => {
    mockAllSources('tolkien')

    renderPanel({ query: 'tolkien', staffFilter: 'patron' as StaffSearchEntityType })

    expect(await screen.findByText('Tolkien Fan')).toBeInTheDocument()
    // Other types must be filtered out.
    expect(screen.queryByText('Tolkien Librarian')).not.toBeInTheDocument()
    expect(screen.queryByText(/Lord of the Rings/)).not.toBeInTheDocument()
    expect(screen.queryByText('PO-tolkien-1')).not.toBeInTheDocument()
    expect(screen.queryByText(/Tolkien reading club/)).not.toBeInTheDocument()
  })

  it('clicking a result navigates to result.route', async () => {
    mockAllSources('tolkien')
    const onClose = vi.fn()

    renderPanel({ query: 'tolkien', staffFilter: 'patron' as StaffSearchEntityType, onClose })

    const patronButton = await screen.findByRole('button', { name: /Tolkien Fan/ })
    await userEvent.click(patronButton)

    expect(mocks.navigate).toHaveBeenCalledWith('/staff/patrons')
    expect(onClose).toHaveBeenCalled()
  })

  it('renders the "no results" message when all data sources return empty', async () => {
    mocks.searchPatrons.mockResolvedValue({ patrons: [], total: 0, page: 1, per_page: 20 })
    mocks.listStaff.mockResolvedValue({ staff: [], total: 0, page: 1, per_page: 25 })
    mocks.searchCatalog.mockResolvedValue({ items: [], total: 0, page: 1, per_page: 25, pages: 0 })
    mocks.getPurchaseOrders.mockResolvedValue({ items: [], total: 0, page: 1, per_page: 100 })
    mocks.getEvents.mockResolvedValue({
      data: [],
      pagination: { page: 1, per_page: 50, total: 0, total_pages: 0, has_next: false, has_previous: false },
    })

    // Use a query that won't match anything in the static staff-nav index either.
    renderPanel({ query: 'zzqxyy', staffFilter: 'patron' as StaffSearchEntityType })

    expect(await screen.findByText(/no.*results|barcode/i)).toBeInTheDocument()
  })
})
