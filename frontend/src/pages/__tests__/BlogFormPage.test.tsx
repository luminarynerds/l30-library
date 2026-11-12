/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Publish-checklist contract tests.
 *
 * BlogFormPage.tsx renders the "Image alt text" checklist row via
 * `validateBlogBodyImages(formData.body)`. The validator is exhaustively
 * unit-tested in src/lib/__tests__/blog-image-validation.test.ts; this
 * suite locks in the specific contract the publish checklist relies on
 * so a future refactor of the validator can't silently regress what
 * the editor's "Publish anyway" gate is checking for.
 */
import { describe, it, expect } from "vitest"
import { validateBlogBodyImages } from "@/lib/blog-image-validation"

describe("BlogFormPage publish-checklist contract", () => {
  it("flags body with <img> lacking any alt attribute", () => {
    const r = validateBlogBodyImages('<p><img src="/a.png"></p>')
    expect(r.valid).toBe(false)
    expect(r.failingImages).toBe(1)
    expect(r.totalImages).toBe(1)
  })

  it("accepts body with <img alt='Real description'>", () => {
    const r = validateBlogBodyImages('<p><img src="/a.png" alt="Real description"></p>')
    expect(r.valid).toBe(true)
    expect(r.failingImages).toBe(0)
  })

  it("accepts body with <img alt='' role='presentation'>", () => {
    const r = validateBlogBodyImages('<p><img src="/a.png" alt="" role="presentation"></p>')
    expect(r.valid).toBe(true)
    expect(r.failingImages).toBe(0)
  })

  it("flags body with <img alt=''> with NO role -- the WCAG silent-gap case", () => {
    const r = validateBlogBodyImages('<p><img src="/a.png" alt=""></p>')
    expect(r.valid).toBe(false)
    expect(r.failingImages).toBe(1)
  })

  it("accepts body with no images at all", () => {
    const r = validateBlogBodyImages("<p>Just words.</p>")
    expect(r.valid).toBe(true)
    expect(r.totalImages).toBe(0)
  })
})
