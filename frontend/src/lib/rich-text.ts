/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Helpers for feeding stored content into the TipTap RichTextEditor.
 *
 * Lesson bodies authored before the WYSIWYG are plain Markdown. TipTap expects
 * HTML, so loading raw Markdown would show literal `**bold**`. `toEditorHtml`
 * converts legacy Markdown to HTML on load (same detection the patron-side
 * MarkdownContent uses); content already saved as HTML passes through untouched.
 */
import MarkdownIt from "markdown-it"

const md = new MarkdownIt({
  html: true,
  linkify: true,
  breaks: false,
  typographer: false,
})

/** True if the content already looks like HTML (block tags present). */
function isHtml(text: string): boolean {
  return /<(p|div|h[1-6]|ul|ol|table|br)\b/i.test(text)
}

/** Convert stored content to HTML suitable for TipTap's `setContent`. */
export function toEditorHtml(content: string): string {
  if (!content) return ""
  return isHtml(content) ? content : md.render(content)
}
