/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from "vitest"
import { validateBlogBodyImages } from "../blog-image-validation"

describe("validateBlogBodyImages", () => {
  it("returns valid for empty body", () => {
    const r = validateBlogBodyImages("")
    expect(r.valid).toBe(true)
    expect(r.totalImages).toBe(0)
    expect(r.failingImages).toBe(0)
  })

  it("returns valid for body without images", () => {
    const r = validateBlogBodyImages("<p>Just text, no images here.</p>")
    expect(r.valid).toBe(true)
    expect(r.totalImages).toBe(0)
  })

  it("accepts <img> with non-empty alt", () => {
    const r = validateBlogBodyImages('<p><img src="/a.png" alt="A diagram"></p>')
    expect(r.valid).toBe(true)
    expect(r.totalImages).toBe(1)
    expect(r.failingImages).toBe(0)
  })

  it("rejects <img> with no alt attribute at all", () => {
    const r = validateBlogBodyImages('<p><img src="/a.png"></p>')
    expect(r.valid).toBe(false)
    expect(r.failingImages).toBe(1)
  })

  it("rejects <img> with empty alt='' and NO role='presentation' (the WCAG gap)", () => {
    const r = validateBlogBodyImages('<p><img src="/a.png" alt=""></p>')
    expect(r.valid).toBe(false)
    expect(r.failingImages).toBe(1)
  })

  it("rejects <img> with whitespace-only alt and no role", () => {
    const r = validateBlogBodyImages('<p><img src="/a.png" alt="   "></p>')
    expect(r.valid).toBe(false)
    expect(r.failingImages).toBe(1)
  })

  it("accepts <img alt='' role='presentation'> as decorative", () => {
    const r = validateBlogBodyImages('<p><img src="/a.png" alt="" role="presentation"></p>')
    expect(r.valid).toBe(true)
    expect(r.failingImages).toBe(0)
  })

  it("accepts <img alt='' role='none'> as decorative", () => {
    const r = validateBlogBodyImages('<p><img src="/a.png" alt="" role="none"></p>')
    expect(r.valid).toBe(true)
  })

  it("handles mixed: valid + invalid in same body", () => {
    const html =
      '<p><img src="/a.png" alt="Good"></p>' +
      '<p><img src="/b.png" alt=""></p>' +
      '<p><img src="/c.png" alt="" role="presentation"></p>' +
      '<p><img src="/d.png"></p>'
    const r = validateBlogBodyImages(html)
    expect(r.totalImages).toBe(4)
    expect(r.failingImages).toBe(2) // b and d
    expect(r.valid).toBe(false)
  })

  it("handles single-quoted attributes", () => {
    const r = validateBlogBodyImages("<p><img src='/a.png' alt='From single quotes'></p>")
    expect(r.valid).toBe(true)
  })

  it("handles attributes with extra whitespace", () => {
    const r = validateBlogBodyImages('<p><img   src="/a.png"   alt="Spaced out"></p>')
    expect(r.valid).toBe(true)
  })

  it("ignores false-positive substrings like '<img' in plain text content", () => {
    // The DOMParser correctly treats this as text, not as a tag
    const r = validateBlogBodyImages("<p>The string &lt;img&gt; appears here as text.</p>")
    expect(r.totalImages).toBe(0)
    expect(r.valid).toBe(true)
  })
})
