/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from "vitest"
import { toEditorHtml } from "../rich-text"

describe("toEditorHtml", () => {
  it("returns empty string for empty content", () => {
    expect(toEditorHtml("")).toBe("")
  })

  it("converts legacy Markdown to HTML", () => {
    const html = toEditorHtml("# Title\n\nSome **bold** text")
    expect(html).toContain("<h1>Title</h1>")
    expect(html).toContain("<strong>bold</strong>")
  })

  it("converts Markdown lists", () => {
    const html = toEditorHtml("- one\n- two")
    expect(html).toContain("<ul>")
    expect(html).toContain("<li>one</li>")
  })

  it("passes existing HTML through untouched (idempotent)", () => {
    const existing = "<p>Already <em>HTML</em></p>"
    expect(toEditorHtml(existing)).toBe(existing)
  })
})
