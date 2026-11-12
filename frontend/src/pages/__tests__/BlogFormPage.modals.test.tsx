/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Integration tests for the two BlogFormPage modal flows that replaced
 * native browser dialogs: version-restore (was window.confirm) and link-URL
 * insertion (was window.prompt added in Task 5).
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter, Routes, Route } from "react-router-dom"

vi.mock("react-hot-toast", () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock("@/components/shells/AdminShell", () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ token: "test-token", user: { id: 1, role: "staff" } }),
}))

const chainMock = {
  focus: vi.fn().mockReturnThis(),
  setLink: vi.fn().mockReturnThis(),
  setContent: vi.fn().mockReturnThis(),
  run: vi.fn(),
}
const editorMock = {
  chain: () => chainMock,
  commands: { setContent: vi.fn() },
  isActive: () => false,
  getAttributes: () => ({}),
  getHTML: () => "",
  getText: () => "",
  on: vi.fn(),
  off: vi.fn(),
}
vi.mock("@tiptap/react", () => ({
  useEditor: () => editorMock,
  EditorContent: () => <div data-testid="editor-content" />,
}))
// StarterKit must expose .configure() since BlogFormPage calls StarterKit.configure({...})
vi.mock("@tiptap/starter-kit", () => ({ default: { configure: () => ({}) } }))
vi.mock("@tiptap/extension-link", () => ({ default: { configure: () => ({}) } }))
vi.mock("@/extensions/blog-image", () => ({ BlogImage: { configure: () => ({}) } }))
vi.mock("@/extensions/callout", () => ({ Callout: { configure: () => ({}) } }))

vi.mock("@/components/AutoSaveIndicator", () => ({
  default: () => <div data-testid="auto-save-indicator" />,
}))
vi.mock("@/components/blog/ImageAltModal", () => ({
  default: () => null,
}))
vi.mock("@/components/blog/MediaLibraryPanel", () => ({
  default: () => null,
}))
vi.mock("@/hooks/useAutoSave", () => ({
  useAutoSave: () => ({ saving: false, lastSavedAt: null, isDirty: false }),
}))

// ConfirmDialog deps
vi.mock("@/features/accessibility/hooks/useUnifiedAccessibility", () => ({
  useUnifiedAccessibility: () => ({
    settings: { sensory: { reduceMotion: false } },
  }),
}))
vi.mock("focus-trap-react", () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

const mockGetAdminPost = vi.fn()
const mockGetPostVersions = vi.fn()
const mockGetPostVersion = vi.fn()
const mockRestorePostVersion = vi.fn()
const mockGetBlogTags = vi.fn()
const mockUpdateBlogPost = vi.fn()
const mockCreateBlogPost = vi.fn()
const mockScheduleBlogPost = vi.fn()
const mockUploadBlogMedia = vi.fn()

vi.mock("@/services/blog-api", () => ({
  createBlogPost: (...args: unknown[]) => mockCreateBlogPost(...args),
  updateBlogPost: (...args: unknown[]) => mockUpdateBlogPost(...args),
  scheduleBlogPost: (...args: unknown[]) => mockScheduleBlogPost(...args),
  getAdminPost: (...args: unknown[]) => mockGetAdminPost(...args),
  getPostVersions: (...args: unknown[]) => mockGetPostVersions(...args),
  getPostVersion: (...args: unknown[]) => mockGetPostVersion(...args),
  restorePostVersion: (...args: unknown[]) => mockRestorePostVersion(...args),
  uploadBlogMedia: (...args: unknown[]) => mockUploadBlogMedia(...args),
  getBlogTags: (...args: unknown[]) => mockGetBlogTags(...args),
}))

import BlogFormPage from "../BlogFormPage"

const MOCK_POST = {
  id: 42,
  title: "Sample Post",
  slug: "sample-post",
  body: "<p>Body</p>",
  tldr: "",
  meta_description: "",
  featured_image: "",
  author_name: "Marlene W.",
  author_role: "Director",
  status: "draft",
  series_name: "",
  series_order: null,
  tags: [],
}
const MOCK_VERSION = {
  id: 99,
  post_id: 42,
  version_number: 1,
  title: "Sample Post",
  created_at: "2026-05-26T00:00:00Z",
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/staff/blog/42/edit"]}>
      <Routes>
        <Route path="/staff/blog/:id/edit" element={<BlogFormPage />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mockGetAdminPost.mockResolvedValue(MOCK_POST)
  mockGetPostVersions.mockResolvedValue([MOCK_VERSION])
  mockGetBlogTags.mockResolvedValue([])
  mockGetPostVersion.mockResolvedValue({ ...MOCK_POST, id: MOCK_VERSION.id, body: "<p>Old body</p>" })
  mockRestorePostVersion.mockResolvedValue({ ...MOCK_POST, body: "<p>Restored</p>" })
  chainMock.run.mockReset()
})

/** Open the Versions panel, then drill into the first version detail view. */
async function openVersionDetail() {
  fireEvent.click(screen.getByRole("button", { name: /Versions/i }))
  await waitFor(() => expect(mockGetPostVersions).toHaveBeenCalled())
  // Click the version row (labelled "v1 Sample Post ...") to enter detail view
  fireEvent.click(await screen.findByRole("button", { name: /v1/i }))
  await waitFor(() => expect(mockGetPostVersion).toHaveBeenCalled())
}

describe("BlogFormPage version restore modal", () => {
  it("opens an accessible ConfirmDialog (not window.confirm) when Restore is clicked", async () => {
    // Ensure window.confirm exists so vi.spyOn can wrap it
    if (typeof window.confirm !== "function") {
      Object.defineProperty(window, "confirm", { writable: true, value: vi.fn() })
    }
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false)
    renderPage()
    await waitFor(() => expect(mockGetAdminPost).toHaveBeenCalled())

    await openVersionDetail()

    // "Restore this version" button in the detail view — matches /Restore/i
    fireEvent.click(await screen.findByRole("button", { name: /Restore this version/i }))

    expect(
      await screen.findByRole("heading", { name: "Restore this version?" })
    ).toBeInTheDocument()
    expect(
      screen.getByText(/current content will be saved as a new version/i)
    ).toBeInTheDocument()
    expect(confirmSpy).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })

  it("calls restorePostVersion when the dialog confirm is clicked", async () => {
    renderPage()
    await waitFor(() => expect(mockGetAdminPost).toHaveBeenCalled())

    await openVersionDetail()
    fireEvent.click(await screen.findByRole("button", { name: /Restore this version/i }))
    fireEvent.click(await screen.findByRole("button", { name: /Restore version/i }))

    await waitFor(() => {
      expect(mockRestorePostVersion).toHaveBeenCalledWith("test-token", 42, MOCK_VERSION.id)
    })
  })

  it("does not call restorePostVersion when the dialog is cancelled", async () => {
    renderPage()
    await waitFor(() => expect(mockGetAdminPost).toHaveBeenCalled())

    await openVersionDetail()
    fireEvent.click(await screen.findByRole("button", { name: /Restore this version/i }))
    fireEvent.click(await screen.findByRole("button", { name: /Go back|Cancel/i }))

    expect(mockRestorePostVersion).not.toHaveBeenCalled()
  })
})


describe("BlogFormPage — link URL modal", () => {
  it("opens an inline modal (not window.prompt) when the Link toolbar button is clicked", async () => {
    if (typeof window.prompt !== "function") {
      Object.defineProperty(window, "prompt", { writable: true, value: vi.fn() })
    }
    const promptSpy = vi.spyOn(window, "prompt").mockReturnValue(null)
    renderPage()
    await waitFor(() => expect(mockGetAdminPost).toHaveBeenCalled())

    fireEvent.click(screen.getByRole("button", { name: /^Link$|Insert link|Add link/i }))

    expect(await screen.findByLabelText(/^URL$/i)).toBeInTheDocument()
    expect(promptSpy).not.toHaveBeenCalled()
    promptSpy.mockRestore()
  })

  it("calls editor.chain().focus().setLink({ href }).run() when Insert is clicked with a non-empty URL", async () => {
    renderPage()
    await waitFor(() => expect(mockGetAdminPost).toHaveBeenCalled())

    fireEvent.click(screen.getByRole("button", { name: /^Link$|Insert link|Add link/i }))
    const input = await screen.findByLabelText(/^URL$/i)
    fireEvent.change(input, { target: { value: "https://example.com" } })
    fireEvent.click(screen.getByRole("button", { name: /^Insert$/i }))

    await waitFor(() => {
      expect(chainMock.setLink).toHaveBeenCalledWith({ href: "https://example.com" })
      expect(chainMock.run).toHaveBeenCalled()
    })
  })

  it("does not call setLink when the modal is cancelled", async () => {
    chainMock.setLink.mockClear()
    chainMock.run.mockClear()
    renderPage()
    await waitFor(() => expect(mockGetAdminPost).toHaveBeenCalled())

    fireEvent.click(screen.getByRole("button", { name: /^Link$|Insert link|Add link/i }))
    await screen.findByLabelText(/^URL$/i)
    fireEvent.click(screen.getByRole("button", { name: /^Cancel$/i }))

    expect(chainMock.setLink).not.toHaveBeenCalled()
  })

  it("does not call setLink when the URL is empty/whitespace", async () => {
    chainMock.setLink.mockClear()
    chainMock.run.mockClear()
    renderPage()
    await waitFor(() => expect(mockGetAdminPost).toHaveBeenCalled())

    fireEvent.click(screen.getByRole("button", { name: /^Link$|Insert link|Add link/i }))
    const input = await screen.findByLabelText(/^URL$/i)
    fireEvent.change(input, { target: { value: "   " } })
    fireEvent.click(screen.getByRole("button", { name: /^Insert$/i }))

    expect(chainMock.setLink).not.toHaveBeenCalled()
  })
})
