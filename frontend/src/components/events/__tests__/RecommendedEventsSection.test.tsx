/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Regression coverage for the recommended-events pagination bug. The
 * section must source its own upcoming-events list (not the parent's
 * filtered page) so recommendations never disappear because the user
 * narrowed the main list.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import RecommendedEventsSection from "../RecommendedEventsSection"

const mocks = vi.hoisted(() => ({
  getEvents: vi.fn(),
}))

vi.mock("@/api/events-api", () => ({
  getEvents: mocks.getEvents,
}))

vi.mock("@/i18n", () => ({
  t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => {
    if (typeof paramsOrFallback === "string") return paramsOrFallback
    if (paramsOrFallback) return `${key}:${JSON.stringify(paramsOrFallback)}`
    return key
  },
}))

// HorizontalEventCarousel pulls in DOM measurement / scrolling code that
// jsdom can't emulate well; stub to a minimal list so we can assert
// which events were handed off.
vi.mock("../HorizontalEventCarousel", () => ({
  __esModule: true,
  default: ({ events }: { events: Array<{ id: number; title: string }> }) => (
    <ul data-testid="carousel">
      {events.map(e => (
        <li key={e.id} data-testid={`carousel-event-${e.id}`}>{e.title}</li>
      ))}
    </ul>
  ),
}))

function makeEvent(id: number, opts: Partial<{ title: string; category: string | null; audience: string | null; start_time: string }> = {}) {
  const inOneWeek = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()
  return {
    id,
    title: opts.title ?? `Event ${id}`,
    description: null,
    start_time: opts.start_time ?? inOneWeek,
    end_time: null,
    location: null,
    is_virtual: false,
    audience: opts.audience ?? null,
    category: opts.category ?? null,
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

function renderSection(props: Partial<React.ComponentProps<typeof RecommendedEventsSection>> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  const merged: React.ComponentProps<typeof RecommendedEventsSection> = {
    preferences: { categories: ["Tech"], audiences: [] },
    matchesPreferences: (cat) => cat === "Tech",
    onToggleBookmark: vi.fn(),
    isBookmarked: () => false,
    onViewEvent: vi.fn(),
    onRegister: vi.fn(),
    isRegistered: () => false,
    onOpenPreferences: vi.fn(),
    ...props,
  }
  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <RecommendedEventsSection {...merged} />
      </QueryClientProvider>
    ),
    props: merged,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe("RecommendedEventsSection", () => {
  it("does not fetch when the user has no preferences set", () => {
    renderSection({
      preferences: { categories: [], audiences: [] },
      matchesPreferences: () => false,
    })
    expect(mocks.getEvents).not.toHaveBeenCalled()
    expect(screen.getByText(/Get Personalized Recommendations/i)).toBeInTheDocument()
  })

  it("fetches its own upcoming events independently of parent pagination/filter", async () => {
    mocks.getEvents.mockResolvedValueOnce({
      data: [
        makeEvent(1, { title: "A Tech Talk", category: "Tech" }),
        makeEvent(2, { title: "A Cooking Class", category: "Food" }),
      ],
      pagination: { page: 1, per_page: 50, total: 2, total_pages: 1, has_next: false, has_previous: false },
    })

    renderSection({
      preferences: { categories: ["Tech"], audiences: [] },
      matchesPreferences: (cat) => cat === "Tech",
    })

    await waitFor(() => expect(mocks.getEvents).toHaveBeenCalledTimes(1))
    expect(mocks.getEvents).toHaveBeenCalledWith({ upcoming: true, per_page: 50 })

    await waitFor(() => {
      expect(screen.getByTestId("carousel-event-1")).toBeInTheDocument()
    })
    // Non-matching event must not be in the carousel.
    expect(screen.queryByTestId("carousel-event-2")).not.toBeInTheDocument()
  })

  it("renders the empty-state CTA when the dedicated fetch returns no matching events", async () => {
    mocks.getEvents.mockResolvedValueOnce({
      data: [makeEvent(99, { category: "Food" })],
      pagination: { page: 1, per_page: 50, total: 1, total_pages: 1, has_next: false, has_previous: false },
    })

    renderSection({
      preferences: { categories: ["Tech"], audiences: [] },
      matchesPreferences: (cat) => cat === "Tech",
    })

    await waitFor(() => expect(mocks.getEvents).toHaveBeenCalled())
    await waitFor(() => {
      expect(screen.getByText("events.recommendedSection.emptyState")).toBeInTheDocument()
    })
  })
})
