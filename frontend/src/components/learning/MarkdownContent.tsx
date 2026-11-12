/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * MarkdownContent - Renders markdown or HTML content safely.
 * Detects format automatically: if content has HTML tags, renders as HTML.
 * Otherwise, converts markdown to HTML via markdown-it. Always sanitizes output.
 */
import { useMemo } from 'react'
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'

const DOMPURIFY_CONFIG = {
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 's', 'del', 'a', 'p', 'br', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre', 'div', 'span', 'section', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'img', 'details', 'summary', 'dl', 'dt', 'dd'],
  ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'id', 'src', 'alt', 'width', 'height'],
  KEEP_CONTENT: true
}

// Force rel="noopener noreferrer" on anchors that open new tabs or point at external hosts.
// Prevents tabnabbing (target=_blank without rel) and leaks of referrer to third parties.
let relHookRegistered = false
function ensureRelHook() {
  if (relHookRegistered) return
  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    if (!(node instanceof Element) || node.tagName !== 'A') return
    const target = node.getAttribute('target')
    const href = node.getAttribute('href') || ''
    const isExternal = /^https?:\/\//i.test(href) || /^\/\//.test(href)
    if (target === '_blank' || isExternal) {
      node.setAttribute('rel', 'noopener noreferrer')
    }
  })
  relHookRegistered = true
}

function isHtml(text: string): boolean {
  return /<(p|div|h[1-6]|ul|ol|table|br)\b/i.test(text)
}

// markdown-it CommonMark + GFM-flavored extras (tables, strikethrough, autolink)
// html: true lets authored HTML pass through to DOMPurify which is the final gate.
const md = new MarkdownIt({
  html: true,
  linkify: true,
  breaks: false,
  typographer: false,
})

interface MarkdownContentProps {
  content: string
  className?: string
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  const html = useMemo(() => {
    if (!content) return ''
    ensureRelHook()
    const source = isHtml(content) ? content : md.render(content)
    return DOMPurify.sanitize(source, DOMPURIFY_CONFIG)
  }, [content])

  if (!html) return null

  return (
    <div
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
