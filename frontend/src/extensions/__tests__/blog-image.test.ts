/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * End-to-end smoke test for the BlogImage TipTap extension.
 *
 * The publish-checklist + accessibility story depends on `role="presentation"`
 * surviving the round-trip `setImage({...role}) -> editor.getHTML() ->
 * DOMPurify.sanitize() -> rendered HTML`. The default @tiptap/extension-image
 * drops unknown attrs silently, so we extend it. This test locks in the
 * contract; if a TipTap upgrade ever drops the role attr again, this test
 * fails loudly instead of letting decorative images sneak past WCAG checks.
 */
import { describe, it, expect, afterEach } from "vitest"
import { Editor } from "@tiptap/core"
import StarterKit from "@tiptap/starter-kit"
import DOMPurify from "dompurify"
import { BlogImage } from "../blog-image"

// Undestroyed editors leave internal timers running; one firing after worker
// teardown surfaces as an unhandled error that fails the whole suite run
// even with every test green (seen in the deploy gate on 2026-07-04).
let editors: Editor[] = []

afterEach(() => {
  for (const e of editors) e.destroy()
  editors = []
})

function getEditor() {
  const editor = new Editor({
    extensions: [StarterKit, BlogImage],
  })
  editors.push(editor)
  return editor
}

describe("BlogImage extension", () => {
  it("preserves role attribute through setImage and getHTML", () => {
    const editor = getEditor()
    editor.commands.setImage({ src: "/a.png", alt: "", role: "presentation" })
    const html = editor.getHTML()
    expect(html).toMatch(/role="presentation"/)
    expect(html).toMatch(/alt=""/)
  })

  it("omits role attr when no role is provided (non-decorative path)", () => {
    const editor = getEditor()
    editor.commands.setImage({ src: "/a.png", alt: "Real description" })
    const html = editor.getHTML()
    expect(html).toMatch(/alt="Real description"/)
    expect(html).not.toMatch(/role=/)
  })

  it("DOMPurify default sanitize preserves role='presentation' on <img>", () => {
    // BlogDetailPage uses DOMPurify.sanitize with ADD_ATTR for callouts only.
    // If a future bump to DOMPurify ever drops `role` from the default
    // allowlist, this test catches it before the WCAG fix becomes invisible
    // on the published render side.
    const dirty = '<img src="/a.png" alt="" role="presentation">'
    // Workaround: under happy-dom, DOMPurify's sanitize() drops the tag of a
    // fragment's sole/first top-level element (confirmed via isolated repro;
    // doesn't happen in real browsers or jsdom). A leading whitespace text
    // node sidesteps it without changing the sanitized result.
    const clean = DOMPurify.sanitize(` ${dirty}`, { ADD_ATTR: ["data-callout-type"] }).replace(/^ /, '')
    expect(clean).toMatch(/role="presentation"/)
    expect(clean).toMatch(/alt=""/)
  })
})
