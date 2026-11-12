/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    language: 'en',
    t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => {
      if (typeof paramsOrFallback === 'string') return paramsOrFallback
      if (paramsOrFallback && typeof paramsOrFallback === 'object') {
        return key + ':' + JSON.stringify(paramsOrFallback)
      }
      return key
    },
    isRTL: false,
    setLanguage: vi.fn(),
  }),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, role: 'admin' }, token: 'test-token' }),
}))

vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/ui/ModalBackdrop', () => ({
  ModalBackdrop: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

const mockList = vi.fn()
const mockCreate = vi.fn()
const mockUpdate = vi.fn()
const mockDelete = vi.fn()
vi.mock('@/api/domains/services/program-partners-api', () => ({
  listProgramPartners: (...args: unknown[]) => mockList(...args),
  createProgramPartner: (...args: unknown[]) => mockCreate(...args),
  updateProgramPartner: (...args: unknown[]) => mockUpdate(...args),
  deleteProgramPartner: (...args: unknown[]) => mockDelete(...args),
}))

// Import after mocks
import StaffProgramPartnersPage from '../StaffProgramPartnersPage'

function emptyResult() {
  return {
    data: [],
    pagination: {
      page: 1, per_page: 20, total: 0, total_pages: 0,
      has_next: false, has_previous: false,
    },
  }
}

function withRows(rows: Array<Record<string, unknown>>) {
  return {
    data: rows,
    pagination: {
      page: 1, per_page: 20, total: rows.length, total_pages: 1,
      has_next: false, has_previous: false,
    },
  }
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/staff/program-partners']}>
        <StaffProgramPartnersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const SAMPLE = {
  id: 11,
  name: 'Friends of the Library',
  slug: 'friends_of_the_library',
  website: 'https://friends.example.org',
  contact_email: 'friends@example.org',
  contact_phone: '555-0100',
  notes: null,
  is_active: true,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-05-01T00:00:00Z',
}

beforeEach(() => {
  mockList.mockReset()
  mockCreate.mockReset()
  mockUpdate.mockReset()
  mockDelete.mockReset()
})

describe('StaffProgramPartnersPage', () => {
  it('renders empty state when 0 results and no filters', async () => {
    mockList.mockResolvedValue(emptyResult())
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/No partner organizations yet/)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /Add your first partner/ })).toBeInTheDocument()
  })

  it('renders rows from the list endpoint', async () => {
    mockList.mockResolvedValue(withRows([SAMPLE]))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Friends of the Library')).toBeInTheDocument()
    })
    expect(screen.getByText('friends@example.org')).toBeInTheDocument()
    expect(screen.getByText('555-0100')).toBeInTheDocument()
  })

  it('debounces search input by ~300ms before refetching with search= param', async () => {
    mockList.mockResolvedValue(withRows([SAMPLE]))
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => expect(mockList).toHaveBeenCalled())
    const initialCalls = mockList.mock.calls.length

    const input = screen.getByPlaceholderText(/Search by name/)
    await user.type(input, 'friends')

    // Eventually a new fetch with `search=friends` fires (debounced).
    await waitFor(
      () => {
        const calls = mockList.mock.calls
        expect(calls.length).toBeGreaterThan(initialCalls)
        expect(calls[calls.length - 1]![0].search).toBe('friends')
      },
      { timeout: 2000 },
    )
  })

  it('passes include_inactive=true when toggle is checked', async () => {
    mockList.mockResolvedValue(withRows([SAMPLE]))
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => expect(mockList).toHaveBeenCalled())

    await user.click(screen.getByLabelText(/Show inactive/))

    await waitFor(() => {
      const callArgs = mockList.mock.calls.map((c) => c[0])
      expect(callArgs.some((a) => a?.include_inactive === true)).toBe(true)
    })
  })

  it('opens the form when "Add partner" is clicked', async () => {
    mockList.mockResolvedValue(withRows([SAMPLE]))
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => expect(screen.getByText('Friends of the Library')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /^Add partner$/ }))

    expect(screen.getByRole('heading', { name: /Add partner organization/ })).toBeInTheDocument()
  })

  it('shows confirm dialog on Deactivate and DELETE fires on confirm', async () => {
    mockList.mockResolvedValue(withRows([SAMPLE]))
    mockDelete.mockResolvedValue(undefined)
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => expect(screen.getByText('Friends of the Library')).toBeInTheDocument())

    await user.click(screen.getByLabelText(/deactivateAria/))

    expect(screen.getByRole('heading', { name: /Deactivate partner organization/ })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^Deactivate$/ }))

    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith('test-token', 11, false)
    })
  })
})
