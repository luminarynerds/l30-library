/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MyBooksPage from './MyBooksPage'
import { useAuth } from '@/contexts/AuthContext'

// Authenticated patron so the page renders the borrowed-books list instead
// of the sign-in prompt.
vi.mock('@/contexts/AuthContext', async () => {
  const React = await import('react')
  return {
    AuthProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
    useAuth: vi.fn(() => ({
      user: { id: 1, first_name: 'Test', last_name: 'Patron', email: 't@x', role: 'patron' },
      token: 'tok',
      isLoading: false,
      isAuthenticated: true,
    })),
  }
})

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

const { mockCheckout } = vi.hoisted(() => ({
  mockCheckout: {
    access_id: 1,
    ebook_id: 10,
    title: 'The Hobbit',
    author_name: 'J.R.R. Tolkien',
    cover_url: null,
    format: 'epub',
    status: 'active',
    expires_at: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
    download_url: null,
  },
}))

vi.mock('@/api/domains/catalog/metislib-api', () => ({
  getMyMetisLibCheckouts: vi.fn().mockResolvedValue([mockCheckout]),
  returnMetisLibEbook: vi.fn().mockResolvedValue({ status: 'returned' }),
}))

vi.mock('@/lib/api-client', () => {
  const api = {
    get: vi.fn().mockResolvedValue([]),
    post: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  }
  return {
    fetchApi: vi.fn().mockResolvedValue({ items: [] }),
    api,
    default: api,
  }
})

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <MyBooksPage />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('MyBooksPage RatingDialog', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockClear()
  })

  it('opens the return dialog with dialog semantics and named star buttons', async () => {
    const user = userEvent.setup()
    renderPage()

    const returnButton = await screen.findByRole('button', { name: /return/i })
    await user.click(returnButton)

    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(within(dialog).getByRole('heading', { name: /return book/i })).toBeInTheDocument()

    // Star buttons are individually named and expose pressed state.
    const oneStar = within(dialog).getByRole('button', { name: /rate 1 star/i })
    expect(oneStar).toHaveAttribute('aria-pressed', 'false')
    const threeStars = within(dialog).getByRole('button', { name: /rate 3 stars/i })
    await user.click(threeStars)
    expect(threeStars).toHaveAttribute('aria-pressed', 'true')

    // Modal supplies a single labeled close button (no bare X).
    expect(within(dialog).getByRole('button', { name: /close/i })).toBeInTheDocument()
  })

  it('closes the dialog via the Modal close button without leaving stray dialogs', async () => {
    const user = userEvent.setup()
    renderPage()

    const returnButton = await screen.findByRole('button', { name: /return/i })
    await user.click(returnButton)
    await screen.findByRole('dialog')

    const closeButton = screen.getByRole('button', { name: /close/i })
    await user.click(closeButton)

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })
})
