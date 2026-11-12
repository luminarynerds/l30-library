/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Regression coverage for the saved-events pagination bug. The section
 * must resolve bookmarked events by id independently of the active
 * filter/pagination, drop bookmarks that 404, and render an empty
 * state with a CTA when nothing is saved.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import SavedEventsSection from "../SavedEventsSection"

const mocks = vi.hoisted(() => ({
  getEventById: vi.fn(),
}))

vi.mock("@/api/events-api", () => ({
  getEventById: mocks.getEventById,
}))

// Match RegistrationModal.test.tsx i18n mock semantics: missing key returns
// the key, allowing tests to assert by key.
vi.mock("@/i18n", () => ({
  t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => {
    if (typeof paramsOrFallback === "string") return paramsOrFallback
    if (paramsOrFallback) return `${key}:${JSON.stringify(paramsOrFallback)}`
    return key
  },
}))

// EventCard pulls in router and lots of styling -> stub for clarity.
vi.mock("../EventCard", () => ({
  __esModule: true,
  default: ({ event }: { event: { id: number; title: string } }) => (
    <div data-testid={`event-card-${event.id}`}>{event.title}</div>
  ),
}))

function makeEvent(id: number, opts: Partial<{ title: string; start_time: string }> = {}) {
  const inOneWeek = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()
  return {
    id,
    title: opts.title ?? `Event ${id}`,
    description: null,
    start_time: opts.start_time ?? inOneWeek,
    end_time: null,
    location: null,
    is_virtual: false,
    audience: null,
    category: null,
    tags: null,
    max_attendees: null,
    registration_required: false,
    registration_count: 0,
    spots_remaining: null,
    image_url: null,
    is_featured: false,
    series_id: null,
    series_name: null,
    created_at: new Date().toISOString(),
    average_rating: null,
    review_count: 0,
  }
}

function renderSection(props: Partial<React.ComponentProps<typeof SavedEventsSection>> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  const merged: React.ComponentProps<typeof SavedEventsSection> = {
    bookmarkedEventIds: [],
    onToggleBookmark: vi.fn(),
    onRemoveBookmark: vi.fn(),
    onViewEvent: vi.fn(),
    onRegister: vi.fn(),
    isRegistered: () => false,
    ...props,
  }
  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <SavedEventsSection {...merged} />
      </QueryClientProvider>
    ),
    props: merged,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe("SavedEventsSection", () => {
  it("renders empty state with i18n key when no bookmarks", () => {
    renderSection({ bookmarkedEventIds: [] })
    expect(screen.getByText("events.savedSection.emptyState")).toBeInTheDocument()
    expect(screen.getByText("events.savedSection.title")).toBeInTheDocument()
    expect(mocks.getEventById).not.toHaveBeenCalled()
  })

  it("renders a bookmarked event by id even when it would not appear on the current paginated/filtered page", async () => {
    // The fixture event would not survive a filter on the parent list,
    // but the section fetches it directly so it still renders.
    mocks.getEventById.mockResolvedValueOnce(makeEvent(42, { title: "Hidden Bookmark" }))
    renderSection({ bookmarkedEventIds: [42] })

    await waitFor(() => {
      expect(screen.getByTestId("event-card-42")).toBeInTheDocument()
    })
    expect(mocks.getEventById).toHaveBeenCalledWith(42)
  })

  it("does not lose bookmarked events when parent filters change (no events prop dependency)", async () => {
    // The component contract no longer accepts an events array, so a
    // parent filter change cannot drop saved items. We assert by
    // re-rendering identical props and confirming the bookmark renders.
    mocks.getEventById.mockResolvedValue(makeEvent(7, { title: "Persistent" }))
    const { rerender } = renderSection({ bookmarkedEventIds: [7] })
    await waitFor(() => expect(screen.getByTestId("event-card-7")).toBeInTheDocument())

    // Simulate a parent re-render after filter change — same ids, same query cache.
    rerender(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <SavedEventsSection
          bookmarkedEventIds={[7]}
          onToggleBookmark={vi.fn()}
          onRemoveBookmark={vi.fn()}
          onViewEvent={vi.fn()}
          onRegister={vi.fn()}
          isRegistered={() => false}
        />
      </QueryClientProvider>
    )
    await waitFor(() => expect(screen.getByTestId("event-card-7")).toBeInTheDocument())
  })

  it("silently drops a 404 bookmark and calls onRemoveBookmark", async () => {
    const onRemoveBookmark = vi.fn()
    // Build an ApiError-shaped error: isApiError checks `instanceof ApiError`
    // but the mocked module makes that fail; the section also checks `status`.
    // Use the real ApiError class from the api-client module for fidelity.
    const { ApiError } = await import("@/lib/api-client")
    mocks.getEventById.mockRejectedValueOnce(new ApiError("not found", 404, "not found"))
    mocks.getEventById.mockResolvedValueOnce(makeEvent(2, { title: "Still Here" }))

    renderSection({ bookmarkedEventIds: [1, 2], onRemoveBookmark })

    await waitFor(() => {
      expect(onRemoveBookmark).toHaveBeenCalledWith(1)
    })
    // The surviving bookmark still renders.
    await waitFor(() => expect(screen.getByTestId("event-card-2")).toBeInTheDocument())
    // The 404 bookmark does NOT render.
    expect(screen.queryByTestId("event-card-1")).not.toBeInTheDocument()
  })
})
