/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@/__tests__/utils/test-utils"
import ArticleList from "@/components/knowledge-base/ArticleList"
import api from "@/api/api"

vi.mock("@/api/api")

const makeArticle = (overrides: Record<string, unknown>) => ({
  id: 1,
  title: "Closing procedures",
  description: "How to close the library",
  content_type: "procedure",
  category: "Operations",
  view_count: 0,
  bookmark_count: 0,
  helpful_count: 0,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  last_verified_at: null,
  ...overrides,
})

beforeEach(() => {
  vi.clearAllMocks()
})

describe("ArticleList staleness badge", () => {
  it("shows a staleness badge for articles not verified in over a year", async () => {
    const old = new Date(Date.now() - 400 * 864e5).toISOString()
    ;(api.get as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeArticle({ last_verified_at: old, updated_at: old }),
    ])
    render(<ArticleList searchQuery="" />)
    expect(await screen.findByText(/needs review/i)).toBeInTheDocument()
  })

  it("does not show a staleness badge for recently verified articles", async () => {
    const recent = new Date(Date.now() - 30 * 864e5).toISOString()
    ;(api.get as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeArticle({ id: 2, title: "Opening procedures", last_verified_at: recent, updated_at: recent }),
    ])
    render(<ArticleList searchQuery="" />)
    await screen.findByText("Opening procedures")
    expect(screen.queryByText(/needs review/i)).toBeNull()
  })
})
