/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import toast from 'react-hot-toast'

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

// AdminShell is heavy; render children only.
vi.mock('@/components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

// Per-file override of the global AuthContext mock (setup.ts mocks token=null).
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: { id: 1, role: 'staff' } }),
}))

const mockGetAdminPosts = vi.fn()
const mockDeleteBlogPost = vi.fn()
const mockRestoreBlogPost = vi.fn()
const mockGetBlogAnalytics = vi.fn()
const mockPublishBlogPost = vi.fn()
const mockUnpublishBlogPost = vi.fn()
const mockScheduleBlogPost = vi.fn()

vi.mock('@/services/blog-api', () => ({
  getAdminPosts: (...args: unknown[]) => mockGetAdminPosts(...args),
  deleteBlogPost: (...args: unknown[]) => mockDeleteBlogPost(...args),
  restoreBlogPost: (...args: unknown[]) => mockRestoreBlogPost(...args),
  getBlogAnalytics: (...args: unknown[]) => mockGetBlogAnalytics(...args),
  publishBlogPost: (...args: unknown[]) => mockPublishBlogPost(...args),
  unpublishBlogPost: (...args: unknown[]) => mockUnpublishBlogPost(...args),
  scheduleBlogPost: (...args: unknown[]) => mockScheduleBlogPost(...args),
}))

import StaffBlogPage from '../StaffBlogPage'

const PUBLISHED_POST = {
  id: 1,
  title: 'Hello World',
  slug: 'hello-world',
  tldr: null,
  meta_description: null,
  featured_image: null,
  author_name: 'Sam',
  author_role: null,
  status: 'published',
  published_at: '2026-01-01T00:00:00Z',
  scheduled_at: null,
  series_name: null,
  read_time_minutes: 3,
  view_count: 0,
  created_at: '2026-01-01T00:00:00Z',
  deleted_at: null,
  tags: [],
}

const DELETED_POST = {
  ...PUBLISHED_POST,
  id: 2,
  title: 'Old Post',
  slug: 'old-post',
  deleted_at: '2026-05-22T12:00:00Z',
}

function renderPage() {
  return render(
    <MemoryRouter>
      <StaffBlogPage />
    </MemoryRouter>,
  )
}

describe('StaffBlogPage — Trash view', () => {
  beforeEach(() => {
    mockGetAdminPosts.mockReset()
    mockDeleteBlogPost.mockReset()
    mockRestoreBlogPost.mockReset()
    mockGetBlogAnalytics.mockReset()
    mockPublishBlogPost.mockReset()
    mockUnpublishBlogPost.mockReset()
    mockScheduleBlogPost.mockReset()
    vi.mocked(toast.success).mockClear()
    vi.mocked(toast.error).mockClear()
    mockGetBlogAnalytics.mockResolvedValue({
      total_views: 0,
      total_posts: 0,
      published_posts: 0,
      views_last_7_days: 0,
      views_last_30_days: 0,
      top_posts: [],
      views_by_day: [],
    })
    mockGetAdminPosts.mockResolvedValue({
      items: [PUBLISHED_POST],
      total: 1,
      page: 1,
      per_page: 20,
      draft_count: 0,
      published_count: 1,
      scheduled_count: 0,
    })
    mockRestoreBlogPost.mockResolvedValue(undefined)
  })

  it('renders a Trash option in the status filter dropdown', async () => {
    renderPage()
    await waitFor(() => {
      expect(mockGetAdminPosts).toHaveBeenCalled()
    })
    const select = screen.getByLabelText('Filter by status') as HTMLSelectElement
    const options = Array.from(select.options).map((o) => o.value)
    expect(options).toContain('trash')
  })

  it('calls the admin list API with status=trash when Trash is selected', async () => {
    renderPage()
    await waitFor(() => expect(mockGetAdminPosts).toHaveBeenCalled())

    const select = screen.getByLabelText('Filter by status') as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'trash' } })

    await waitFor(() => {
      const calls = mockGetAdminPosts.mock.calls
      const lastCall = calls[calls.length - 1]!
      // signature: getAdminPosts(token, { status, q, page, per_page })
      expect(lastCall[1]).toMatchObject({ status: 'trash' })
    })
  })

  it('shows a Restore button (not Delete) in Trash view and calls restoreBlogPost on click', async () => {
    // First call: no filter, returns published. After switching to trash, return deleted_post.
    mockGetAdminPosts
      .mockResolvedValueOnce({
        items: [PUBLISHED_POST],
        total: 1,
        page: 1,
        per_page: 20,
        draft_count: 0,
        published_count: 1,
        scheduled_count: 0,
      })
      .mockResolvedValue({
        items: [DELETED_POST],
        total: 1,
        page: 1,
        per_page: 20,
        draft_count: 0,
        published_count: 0,
        scheduled_count: 0,
      })

    renderPage()
    await waitFor(() => expect(mockGetAdminPosts).toHaveBeenCalled())

    fireEvent.change(screen.getByLabelText('Filter by status'), {
      target: { value: 'trash' },
    })

    // Wait for the deleted post to render
    await waitFor(() => {
      expect(screen.getByText('Old Post')).toBeInTheDocument()
    })

    // Row action: Restore present; Delete absent.
    const restoreBtn = screen.getByRole('button', { name: /Restore Old Post/i })
    expect(restoreBtn).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Delete Old Post/i })).not.toBeInTheDocument()

    fireEvent.click(restoreBtn)

    await waitFor(() => {
      expect(mockRestoreBlogPost).toHaveBeenCalledWith('test-token', 2)
    })
  })

  it('shows an error toast when restore fails', async () => {
    mockGetAdminPosts
      .mockResolvedValueOnce({
        items: [PUBLISHED_POST],
        total: 1,
        page: 1,
        per_page: 20,
        draft_count: 0,
        published_count: 1,
        scheduled_count: 0,
      })
      .mockResolvedValue({
        items: [DELETED_POST],
        total: 1,
        page: 1,
        per_page: 20,
        draft_count: 0,
        published_count: 0,
        scheduled_count: 0,
      })
    mockRestoreBlogPost.mockRejectedValueOnce(new Error('boom'))

    renderPage()
    await waitFor(() => expect(mockGetAdminPosts).toHaveBeenCalled())

    fireEvent.change(screen.getByLabelText('Filter by status'), {
      target: { value: 'trash' },
    })

    await waitFor(() => {
      expect(screen.getByText('Old Post')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /Restore Old Post/i }))

    await waitFor(() => {
      expect(vi.mocked(toast.error)).toHaveBeenCalledWith('Failed to restore')
    })
  })

  it('hides bulk-selection checkboxes and "Move selected to Trash" button in Trash view', async () => {
    mockGetAdminPosts.mockResolvedValue({
      items: [DELETED_POST],
      total: 1,
      page: 1,
      per_page: 20,
      draft_count: 0,
      published_count: 0,
      scheduled_count: 0,
    })

    renderPage()
    await waitFor(() => expect(mockGetAdminPosts).toHaveBeenCalled())

    fireEvent.change(screen.getByLabelText('Filter by status'), {
      target: { value: 'trash' },
    })

    await waitFor(() => {
      expect(screen.getByText('Old Post')).toBeInTheDocument()
    })

    // No select-all header
    expect(screen.queryByRole('button', { name: /Select all/i })).not.toBeInTheDocument()
    // No row checkbox
    expect(screen.queryByRole('button', { name: /Select Old Post/i })).not.toBeInTheDocument()
    // No "Move selected to Trash" button
    expect(screen.queryByRole('button', { name: /Move selected to Trash/i })).not.toBeInTheDocument()
  })
})

describe("StaffBlogPage — single-delete modal", () => {
  it("row trash-icon button has aria-label \"Move <title> to Trash\"", async () => {
    mockGetAdminPosts.mockResolvedValue({
      items: [PUBLISHED_POST],
      total: 1,
      page: 1,
      per_page: 20,
      draft_count: 0,
      published_count: 1,
      scheduled_count: 0,
    })
    renderPage()
    await waitFor(() => expect(mockGetAdminPosts).toHaveBeenCalled())

    expect(
      screen.getByRole("button", { name: `Move ${PUBLISHED_POST.title} to Trash` })
    ).toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: `Delete ${PUBLISHED_POST.title}` })
    ).not.toBeInTheDocument()
  })

  it("opens a modal with new copy when the trash-icon button is clicked", async () => {
    mockGetAdminPosts.mockResolvedValue({
      items: [PUBLISHED_POST],
      total: 1,
      page: 1,
      per_page: 20,
      draft_count: 0,
      published_count: 1,
      scheduled_count: 0,
    })
    renderPage()
    await waitFor(() => expect(mockGetAdminPosts).toHaveBeenCalled())

    fireEvent.click(
      screen.getByRole("button", { name: `Move ${PUBLISHED_POST.title} to Trash` })
    )

    expect(await screen.findByRole("heading", { name: "Move post to Trash?" })).toBeInTheDocument()
    expect(
      screen.getByText((content) =>
        content.includes("moved to Trash") && content.includes("restore")
      )
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/this cannot be undone/i)
    ).not.toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Move to Trash" })
    ).toBeInTheDocument()
  })

  it("calls deleteBlogPost when the modal confirm button is clicked", async () => {
    mockGetAdminPosts.mockResolvedValue({
      items: [PUBLISHED_POST],
      total: 1,
      page: 1,
      per_page: 20,
      draft_count: 0,
      published_count: 1,
      scheduled_count: 0,
    })
    mockDeleteBlogPost.mockResolvedValue(undefined)
    renderPage()
    await waitFor(() => expect(mockGetAdminPosts).toHaveBeenCalled())

    fireEvent.click(
      screen.getByRole("button", { name: `Move ${PUBLISHED_POST.title} to Trash` })
    )
    fireEvent.click(await screen.findByRole("button", { name: "Move to Trash" }))

    await waitFor(() => {
      expect(mockDeleteBlogPost).toHaveBeenCalledWith("test-token", PUBLISHED_POST.id)
    })
  })

  it('does not call deleteBlogPost when Cancel is clicked', async () => {
    mockDeleteBlogPost.mockReset()
    mockGetAdminPosts.mockResolvedValue({
      items: [PUBLISHED_POST],
      total: 1,
      page: 1,
      per_page: 20,
      draft_count: 0,
      published_count: 1,
      scheduled_count: 0,
    })
    renderPage()
    await waitFor(() => expect(mockGetAdminPosts).toHaveBeenCalled())

    fireEvent.click(
      screen.getByRole('button', { name: `Move ${PUBLISHED_POST.title} to Trash` })
    )
    await screen.findByRole('heading', { name: 'Move post to Trash?' })
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(mockDeleteBlogPost).not.toHaveBeenCalled()
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Move post to Trash?' })).not.toBeInTheDocument()
    })
  })
})

describe('StaffBlogPage — bulk-delete modal', () => {
  it('"Move selected to Trash" button appears in the bulk action bar (not "Delete selected")', async () => {
    mockGetAdminPosts.mockResolvedValue({
      items: [PUBLISHED_POST],
      total: 1,
      page: 1,
      per_page: 20,
      draft_count: 0,
      published_count: 1,
      scheduled_count: 0,
    })
    renderPage()
    await waitFor(() => expect(mockGetAdminPosts).toHaveBeenCalled())

    // Select the row to reveal the bulk action bar
    fireEvent.click(screen.getByRole('button', { name: `Select ${PUBLISHED_POST.title}` }))

    expect(screen.getByRole('button', { name: /Move selected to Trash/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Delete selected/i })).not.toBeInTheDocument()
  })

  it('opens a bulk-delete modal with new copy when the bulk action button is clicked', async () => {
    mockDeleteBlogPost.mockReset()
    mockGetAdminPosts.mockResolvedValue({
      items: [PUBLISHED_POST],
      total: 1,
      page: 1,
      per_page: 20,
      draft_count: 0,
      published_count: 1,
      scheduled_count: 0,
    })
    renderPage()
    await waitFor(() => expect(mockGetAdminPosts).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('button', { name: `Select ${PUBLISHED_POST.title}` }))
    fireEvent.click(screen.getByRole('button', { name: /Move selected to Trash/i }))

    expect(
      await screen.findByRole('heading', { name: 'Move 1 post(s) to Trash?' })
    ).toBeInTheDocument()
    expect(
      screen.getByText(/moved to Trash. You can restore them/i)
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/permanently delete/i)
    ).not.toBeInTheDocument()
  })

  it('calls deleteBlogPost for each selected id when "Move to Trash" is clicked', async () => {
    mockDeleteBlogPost.mockReset()
    mockGetAdminPosts.mockResolvedValue({
      items: [PUBLISHED_POST],
      total: 1,
      page: 1,
      per_page: 20,
      draft_count: 0,
      published_count: 1,
      scheduled_count: 0,
    })
    mockDeleteBlogPost.mockResolvedValue(undefined)
    renderPage()
    await waitFor(() => expect(mockGetAdminPosts).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('button', { name: `Select ${PUBLISHED_POST.title}` }))
    fireEvent.click(screen.getByRole('button', { name: /Move selected to Trash/i }))
    await screen.findByRole('heading', { name: 'Move 1 post(s) to Trash?' })
    fireEvent.click(screen.getByRole('button', { name: 'Move to Trash' }))

    await waitFor(() => {
      expect(mockDeleteBlogPost).toHaveBeenCalledWith('test-token', PUBLISHED_POST.id)
    })
  })

  it('does not call deleteBlogPost when Cancel is clicked', async () => {
    mockDeleteBlogPost.mockReset()
    mockGetAdminPosts.mockResolvedValue({
      items: [PUBLISHED_POST],
      total: 1,
      page: 1,
      per_page: 20,
      draft_count: 0,
      published_count: 1,
      scheduled_count: 0,
    })
    renderPage()
    await waitFor(() => expect(mockGetAdminPosts).toHaveBeenCalled())

    fireEvent.click(screen.getByRole('button', { name: `Select ${PUBLISHED_POST.title}` }))
    fireEvent.click(screen.getByRole('button', { name: /Move selected to Trash/i }))
    await screen.findByRole('heading', { name: 'Move 1 post(s) to Trash?' })
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(mockDeleteBlogPost).not.toHaveBeenCalled()
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Move 1 post(s) to Trash?' })).not.toBeInTheDocument()
    })
  })
})
