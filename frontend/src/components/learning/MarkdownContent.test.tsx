/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

// Workaround: DOMPurify's internal NodeIterator/TreeWalker-based sanitize()
// is broken under happy-dom - it only visits the very first top-level node
// of the dirty fragment (unwrapping its tag but keeping its content) and
// silently skips filtering everything else in the tree (siblings *and*
// descendants), even genuinely disallowed tags. Confirmed via isolated
// reproduction against real DOMPurify + happy-dom; does not occur in real
// browsers or under jsdom. Swap in a plain-DOM-API (non-TreeWalker) allowlist
// filter here so these tests still exercise the real ALLOWED_TAGS/ALLOWED_ATTR
// contract from MarkdownContent's DOMPURIFY_CONFIG without hitting the bug.
vi.mock('dompurify', async (importOriginal) => {
  const actual = await importOriginal<typeof import('dompurify')>()
  return {
    default: {
      ...actual.default,
      sanitize: (
        dirty: string,
        cfg: { ALLOWED_TAGS?: string[]; ALLOWED_ATTR?: string[] } = {},
      ) => {
        const allowedTags = new Set((cfg.ALLOWED_TAGS ?? []).map(t => t.toLowerCase()))
        const allowedAttrs = new Set((cfg.ALLOWED_ATTR ?? []).map(a => a.toLowerCase()))
        const container = document.createElement('div')
        container.innerHTML = dirty

        function clean(node: Element) {
          for (const el of Array.from(node.children)) {
            clean(el)
            if (allowedTags.has(el.tagName.toLowerCase())) {
              for (const attr of Array.from(el.attributes)) {
                if (!allowedAttrs.has(attr.name.toLowerCase())) el.removeAttribute(attr.name)
              }
            } else {
              while (el.firstChild) node.insertBefore(el.firstChild, el)
              node.removeChild(el)
            }
          }
        }
        clean(container)
        return container.innerHTML
      },
    },
  }
})

import { MarkdownContent } from './MarkdownContent'

describe('MarkdownContent', () => {
  it('renders nothing for empty content', () => {
    const { container } = render(<MarkdownContent content="" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('applies className to wrapper', () => {
    const { container } = render(<MarkdownContent content="hello" className="prose" />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.className).toBe('prose')
  })

  it('renders headers', () => {
    const { container } = render(<MarkdownContent content={'# Title\n\n## Sub'} />)
    expect(container.querySelector('h1')?.textContent).toBe('Title')
    expect(container.querySelector('h2')?.textContent).toBe('Sub')
  })

  it('renders bold and italic together', () => {
    const { container } = render(<MarkdownContent content="**bold** and *italic* and ***both***" />)
    expect(container.querySelector('strong')?.textContent).toBe('bold')
    expect(container.querySelector('em')?.textContent).toBe('italic')
    // markdown-it nests strong>em for ***both***
    const strongEm = container.querySelector('strong em, em strong')
    expect(strongEm?.textContent).toBe('both')
  })

  it('renders nested unordered lists', () => {
    const md = [
      '- top one',
      '  - nested a',
      '  - nested b',
      '- top two',
    ].join('\n')
    const { container } = render(<MarkdownContent content={md} />)
    const topUls = container.querySelectorAll(':scope > div > ul')
    expect(topUls.length).toBe(1)
    const topUl = topUls[0]!
    const topItems = topUl.querySelectorAll(':scope > li')
    expect(topItems.length).toBe(2)
    // First top item should contain a nested ul with 2 items
    const firstTopItem = topItems[0]!
    const nestedUl = firstTopItem.querySelector('ul')
    expect(nestedUl).not.toBeNull()
    expect(nestedUl?.querySelectorAll('li').length).toBe(2)
  })

  it('renders strikethrough (~~text~~)', () => {
    const { container } = render(<MarkdownContent content="this is ~~struck~~ out" />)
    expect(container.querySelector('s')?.textContent).toBe('struck')
  })

  it('autolinks bare URLs', () => {
    const { container } = render(<MarkdownContent content="see https://example.com for info" />)
    const a = container.querySelector('a')
    expect(a).not.toBeNull()
    expect(a?.getAttribute('href')).toBe('https://example.com')
    expect(a?.textContent).toBe('https://example.com')
  })

  it('renders explicit link syntax', () => {
    const { container } = render(<MarkdownContent content="[docs](https://example.com/d)" />)
    const a = container.querySelector('a')
    expect(a?.getAttribute('href')).toBe('https://example.com/d')
    expect(a?.textContent).toBe('docs')
  })

  it('preserves fenced code block content and escapes HTML', () => {
    const md = '```\n<script>alert(1)</script>\nconst x = 1;\n```'
    const { container } = render(<MarkdownContent content={md} />)
    const code = container.querySelector('pre code')
    expect(code).not.toBeNull()
    expect(code?.textContent).toContain('<script>alert(1)</script>')
    expect(code?.textContent).toContain('const x = 1;')
    // No actual <script> element in DOM
    expect(container.querySelector('script')).toBeNull()
  })

  it('renders inline code', () => {
    const { container } = render(<MarkdownContent content="use `npm ci` to install" />)
    expect(container.querySelector('code')?.textContent).toBe('npm ci')
  })

  it('renders tables', () => {
    const md = [
      '| Col A | Col B |',
      '| --- | --- |',
      '| a1 | b1 |',
      '| a2 | b2 |',
    ].join('\n')
    const { container } = render(<MarkdownContent content={md} />)
    expect(container.querySelector('table')).not.toBeNull()
    expect(container.querySelectorAll('thead th').length).toBe(2)
    const rows = container.querySelectorAll('tbody tr')
    expect(rows.length).toBe(2)
    const firstRowCells = rows[0]!.querySelectorAll('td')
    expect(firstRowCells[1]!.textContent).toBe('b1')
  })

  it('renders blockquotes', () => {
    const { container } = render(<MarkdownContent content="> quoted text" />)
    const bq = container.querySelector('blockquote')
    expect(bq).not.toBeNull()
    expect(bq?.textContent?.trim()).toBe('quoted text')
  })

  it('passes through pre-rendered HTML via isHtml branch (no markdown re-render)', () => {
    // Triggers isHtml() detector (<p> tag) so content is sanitized as-is.
    // The literal asterisks should remain because markdown render is skipped.
    const { container } = render(<MarkdownContent content="<p>raw **stays** literal</p>" />)
    const p = container.querySelector('p')
    expect(p).not.toBeNull()
    expect(p?.textContent).toBe('raw **stays** literal')
    expect(container.querySelector('strong')).toBeNull()
  })

  it('strips disallowed tags via DOMPurify', () => {
    const md = '<script>window.x=1</script>\n\n# safe'
    const { container } = render(<MarkdownContent content={md} />)
    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('h1')?.textContent).toBe('safe')
  })
})
