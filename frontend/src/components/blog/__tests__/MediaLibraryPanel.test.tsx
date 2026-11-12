/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, within, userEvent } from "@/__tests__/utils/test-utils"

vi.mock("focus-trap-react", () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ token: "test-token", user: { id: 1 } }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

vi.mock("react-hot-toast", () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

const listBlogMediaMock = vi.fn()
const deleteBlogMediaMock = vi.fn()
vi.mock("@/services/blog-api", () => ({
  listBlogMedia: (...args: unknown[]) => listBlogMediaMock(...args),
  deleteBlogMedia: (...args: unknown[]) => deleteBlogMediaMock(...args),
}))

import MediaLibraryPanel from "../MediaLibraryPanel"

function makeMediaItem(i: number) {
  return {
    filename: `image-${i}.png`,
    url: `/media/image-${i}.png`,
    size: 12345 * i,
    uploaded_at: 1716000000 + i,
  }
}

describe("MediaLibraryPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("loads images from listBlogMedia when opened", async () => {
    listBlogMediaMock.mockResolvedValue([makeMediaItem(1), makeMediaItem(2)])
    render(
      <MediaLibraryPanel
        isOpen={true}
        token="test-token"
        onClose={vi.fn()}
        onInsert={vi.fn()}
      />,
    )
    await waitFor(() => expect(listBlogMediaMock).toHaveBeenCalledWith("test-token"))
    await waitFor(() => expect(screen.getByText("image-1.png")).toBeInTheDocument())
    expect(screen.getByText("image-2.png")).toBeInTheDocument()
  })

  it("renders nothing when isOpen is false", () => {
    render(
      <MediaLibraryPanel
        isOpen={false}
        token="test-token"
        onClose={vi.fn()}
        onInsert={vi.fn()}
      />,
    )
    expect(listBlogMediaMock).not.toHaveBeenCalled()
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("shows empty state when no images", async () => {
    listBlogMediaMock.mockResolvedValue([])
    render(
      <MediaLibraryPanel
        isOpen={true}
        token="test-token"
        onClose={vi.fn()}
        onInsert={vi.fn()}
      />,
    )
    await waitFor(() => expect(screen.getByText(/no images uploaded yet/i)).toBeInTheDocument())
  })

  it("Insert button opens the alt-text modal then onInsert is called", async () => {
    const user = userEvent.setup()
    const onInsert = vi.fn()
    const onClose = vi.fn()
    listBlogMediaMock.mockResolvedValue([makeMediaItem(1)])
    render(
      <MediaLibraryPanel
        isOpen={true}
        token="test-token"
        onClose={onClose}
        onInsert={onInsert}
      />,
    )
    await waitFor(() => expect(screen.getByText("image-1.png")).toBeInTheDocument())
    await user.click(screen.getByRole("button", { name: /insert image-1\.png/i }))
    // Alt modal pops up
    await waitFor(() => expect(screen.getByText(/^image alt text$/i)).toBeInTheDocument())
    const altInput = screen.getByRole("textbox", { name: /alt text/i })
    await user.clear(altInput)
    await user.type(altInput, "A test image")
    await user.click(screen.getByRole("button", { name: /^insert image$/i }))
    expect(onInsert).toHaveBeenCalledWith({
      url: "/media/image-1.png",
      alt: "A test image",
      decorative: false,
    })
    expect(onClose).toHaveBeenCalled()
  })

  it("Delete button shows confirm then calls deleteBlogMedia", async () => {
    const user = userEvent.setup()
    listBlogMediaMock.mockResolvedValue([makeMediaItem(1)])
    deleteBlogMediaMock.mockResolvedValue(undefined)
    render(
      <MediaLibraryPanel
        isOpen={true}
        token="test-token"
        onClose={vi.fn()}
        onInsert={vi.fn()}
      />,
    )
    await waitFor(() => expect(screen.getByText("image-1.png")).toBeInTheDocument())
    await user.click(screen.getByRole("button", { name: /delete image-1\.png/i }))
    // Confirm dialog appears
    const confirmHeading = await screen.findByText(/delete image\?/i)
    expect(confirmHeading).toBeInTheDocument()
    // Click the danger confirm
    const confirmBtn = screen.getByRole("button", { name: /^delete image$/i })
    await user.click(confirmBtn)
    await waitFor(() =>
      expect(deleteBlogMediaMock).toHaveBeenCalledWith("test-token", "image-1.png"),
    )
    // Image removed from grid
    await waitFor(() => expect(screen.queryByText("image-1.png")).not.toBeInTheDocument())
  })

  it("Load more reveals additional images beyond page size", async () => {
    const user = userEvent.setup()
    // 60 items -- more than the 50 page size
    const items = Array.from({ length: 60 }, (_, i) => makeMediaItem(i + 1))
    listBlogMediaMock.mockResolvedValue(items)
    render(
      <MediaLibraryPanel
        isOpen={true}
        token="test-token"
        onClose={vi.fn()}
        onInsert={vi.fn()}
      />,
    )
    await waitFor(() => expect(screen.getByText("60 images available")).toBeInTheDocument())
    // Most-recent first: items sorted by uploaded_at desc, so item-60 first
    expect(screen.getByText("image-60.png")).toBeInTheDocument()
    // Items 50..59 are in the next page
    expect(screen.queryByText("image-10.png")).not.toBeInTheDocument()
    const loadMore = screen.getByRole("button", { name: /load more/i })
    await user.click(loadMore)
    await waitFor(() => expect(screen.getByText("image-10.png")).toBeInTheDocument())
  })

  it("does not call list when token is null", () => {
    render(
      <MediaLibraryPanel
        isOpen={true}
        token={null}
        onClose={vi.fn()}
        onInsert={vi.fn()}
      />,
    )
    expect(listBlogMediaMock).not.toHaveBeenCalled()
  })

  it("surfaces an error when the list call fails", async () => {
    listBlogMediaMock.mockRejectedValue(new Error("Network down"))
    render(
      <MediaLibraryPanel
        isOpen={true}
        token="test-token"
        onClose={vi.fn()}
        onInsert={vi.fn()}
      />,
    )
    await waitFor(() => {
      const alert = screen.getByRole("alert")
      expect(within(alert).getByText(/network down/i)).toBeInTheDocument()
    })
  })
})
