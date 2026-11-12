/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
// AdminShell -> StaffLayout now pulls in real Router (useLocation),
// OrganizationFeaturesContext, and accessibility/preferences context — use the
// shared test-utils render (Router + AllProviders) instead of bare RTL render.
import { render } from '../utils/test-utils'
import StaffCatalogingPage from '../../pages/StaffCatalogingPage'

const navigateMock = vi.fn()
const createCatalogItemMock = vi.fn()
const searchCatalogMock = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { role: 'staff' },
    token: 'token-123',
    isLoading: false,
    isAuthenticated: true,
  }),
}))

vi.mock('../../components/staff/BulkOperationsPanel', () => ({
  default: () => null,
  useBulkSelection: () => ({
    selectedIds: [],
    setSelectedIds: vi.fn(),
    toggleSelection: vi.fn(),
    isSelected: vi.fn(),
    selectedCount: 0,
  }),
}))

vi.mock('../../components/print', () => ({
  PrintableBarcode: () => null,
}))

vi.mock('../../api/catalog-api', () => ({
  searchCatalog: (...args: unknown[]) => searchCatalogMock(...args),
  checkDuplicates: vi.fn().mockResolvedValue({ has_duplicates: false, duplicates: [], message: null }),
  bulkUpdateCatalogItems: vi.fn(),
  fetchCoverForItem: vi.fn(),
}))

vi.mock('../../api/cataloging-api', () => ({
  searchZ3950: vi.fn().mockResolvedValue({ results: [] }),
}))

vi.mock('../../api/staff-api/catalog', () => ({
  createCatalogItem: (...args: unknown[]) => createCatalogItemMock(...args),
  updateCatalogItem: vi.fn(),
  deleteCatalogItem: vi.fn(),
  // CatalogQueuePanel (rendered as part of the page) fetches stats on mount.
  getCatalogStats: vi.fn().mockResolvedValue({
    status_counts: {},
    missing_covers: 0,
    added_this_week: 0,
  }),
}))

vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('StaffCatalogingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    searchCatalogMock.mockResolvedValue({ items: [], total: 0, page: 1, per_page: 20, pages: 0 })
    createCatalogItemMock.mockResolvedValue({ id: 99 })
    localStorage.clear()
  })

  it('creates new items via staff catalog API', async () => {
    const { container } = render(<StaffCatalogingPage />)

    fireEvent.click(await screen.findByRole('button', { name: /add item/i }))
    fireEvent.click(await screen.findByRole('button', { name: /skip, enter details manually/i }))

    const titleInput = container.querySelector('input[name="title"]') as HTMLInputElement
    expect(titleInput).toBeTruthy()

    fireEvent.change(titleInput, { target: { value: 'Integration Test Book' } })
    fireEvent.click(screen.getByRole('button', { name: /^create$/i }))

    await waitFor(() => {
      expect(createCatalogItemMock).toHaveBeenCalledWith(
        'token-123',
        expect.objectContaining({ title: 'Integration Test Book', item_type: 'book' })
      )
    })
  })
})
