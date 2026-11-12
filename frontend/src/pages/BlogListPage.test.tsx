/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from "vitest"
import { waitFor } from "@testing-library/react"
import { render } from "@/__tests__/utils/test-utils"

// Mock the blog API so we don't hit network in the test
vi.mock("@/services/blog-api", () => ({
  getBlogPosts: vi.fn().mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    per_page: 12,
    draft_count: 0,
    published_count: 0,
    scheduled_count: 0,
  }),
  getBlogTags: vi.fn().mockResolvedValue([
    { id: 1, name: "Books", slug: "books", post_count: 3 },
  ]),
}))

// Mock branding so library_short_name is deterministic. We delegate to the
// real module for DEFAULT_BRANDING (which has every field I18nProvider reads),
// then override just the few values we care about.
vi.mock("@/contexts/BrandingContext", async (importOriginal) => {
  const actual: typeof import("@/contexts/BrandingContext") = await importOriginal()
  const branding = {
    ...(actual as unknown as { DEFAULT_BRANDING?: object }).DEFAULT_BRANDING,
    // DEFAULT_BRANDING is not exported; fall back to a complete shape if needed.
    library_name: "Test Library",
    library_short_name: "TestLib",
    domain: "https://test.example",
    contact_email: "",
    privacy_email: "",
    indie_email: "",
    giving_email: "",
    events_email: "",
    print_email: "",
    makerspace_email: "",
    phone: "",
    address_line1: "",
    address_line2: "",
    city: "",
    state: "",
    zip_code: "",
    primary_color: "",
    accent_color: "",
    card_prefix: "",
    product_name: "",
    product_tagline: "",
    hero_title: "",
    hero_subtitle: "",
    tagline: "",
    is_demo: false,
    bluesky_url: "",
    mastodon_url: "",
    seasonal_callout_active: false,
  }
  return {
    ...actual,
    useBranding: () => branding,
    useBrandingContext: () => ({
      branding,
      loading: false,
      setupComplete: true,
      hasAdmin: true,
      refetch: async () => {},
    }),
  }
})

import BlogListPage from "@/pages/BlogListPage"
import { MemoryRouter } from "react-router-dom"

function getAlternateLinks(): HTMLLinkElement[] {
  return Array.from(
    document.head.querySelectorAll('link[rel="alternate"][type="application/atom+xml"]'),
  )
}

describe("BlogListPage alternate feed links", () => {
  // No manual head cleanup — the component's useEffect cleanup removes its
  // own links on unmount, and testing-library auto-unmounts after each test.
  // Manually pre-stripping head desyncs React's commit phase with the DOM
  // and makes the cleanup throw NotFoundError on the second test.

  it("renders only the main feed link when no tag is active", async () => {
    render(
      <MemoryRouter initialEntries={["/blog"]}>
        <BlogListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      const links = getAlternateLinks()
      expect(links).toHaveLength(1)
      expect(links[0]!.getAttribute("href")).toBe("/api/v1/blog/feed")
    })
  })

  it("renders a per-tag alternate link when a tag is active", async () => {
    render(
      <MemoryRouter initialEntries={["/blog?tag=books"]}>
        <BlogListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      const links = getAlternateLinks()
      const hrefs = links.map((l) => l.getAttribute("href"))
      expect(hrefs).toContain("/api/v1/blog/feed")
      expect(hrefs).toContain("/api/v1/blog/feed/tag/books")
      expect(links).toHaveLength(2)
    })
  })
})
