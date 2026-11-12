/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'

const BRACKET_RE = /\[([A-Z]+)\]/g

const h3Class = 'text-base font-semibold text-lsc-dark dark:text-lsc-cream mt-4 mb-2'
const olClass = 'list-decimal list-inside space-y-1.5 ml-1'
const ulClass = 'list-disc list-inside space-y-1.5 ml-1'
const liClass = 'text-sm text-lsc-dark/85 dark:text-lsc-cream/85 leading-relaxed'
const pClass = 'text-sm text-lsc-dark/85 dark:text-lsc-cream/85 leading-relaxed'
const badgeClass =
  'inline-block px-1.5 py-0.5 rounded text-xs font-semibold bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'

type LineType = 'numbered' | 'bullet' | 'header' | 'blank' | 'text'

interface ParsedLine {
  type: LineType
  raw: string
  text: string
  indent: number
}

function classifyLine(line: string): ParsedLine {
  const trimmed = line.trimStart()
  const indent = line.length - trimmed.length

  // blank
  if (trimmed === '') {
    return { type: 'blank', raw: line, text: '', indent: 0 }
  }

  // numbered list: "1. ", "2. ", etc.
  const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/)
  if (numMatch) {
    return { type: 'numbered', raw: line, text: numMatch[2]!, indent }
  }

  // bullet list: "• ", "✓ ", "- ", "* "
  const bulletMatch = trimmed.match(/^[•✓\-*]\s+(.*)/)
  if (bulletMatch) {
    return { type: 'bullet', raw: line, text: bulletMatch[1]!, indent }
  }

  // section header: short line ending with ":" (not inside a list context -- handled by grouping)
  if (trimmed.endsWith(':') && trimmed.length < 60 && !trimmed.match(/^\d+\./)) {
    return { type: 'header', raw: line, text: trimmed.replace(/:$/, ''), indent }
  }

  return { type: 'text', raw: line, text: trimmed, indent }
}

function renderInline(text: string, parentKey: string): React.ReactNode {
  const parts: React.ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  // Reset regex state
  BRACKET_RE.lastIndex = 0

  while ((match = BRACKET_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }
    parts.push(
      <span key={`${parentKey}-badge-${match.index}`} className={badgeClass}>
        {match[1]}
      </span>
    )
    lastIndex = BRACKET_RE.lastIndex
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return parts.length === 1 ? parts[0]! : <>{parts}</>
}

function buildSubItems(
  lines: ParsedLine[],
  startIdx: number,
  parentIndent: number,
  keyPrefix: string
): { element: React.ReactElement | null; consumed: number } {
  const items: React.ReactNode[] = []
  let i = startIdx

  while (i < lines.length) {
    const ln = lines[i]!
    if (ln.type !== 'bullet' || ln.indent <= parentIndent) break
    items.push(
      <li key={`${keyPrefix}-sub-${i}`} className={liClass}>
        {renderInline(ln.text, `${keyPrefix}-sub-${i}`)}
      </li>
    )
    i++
  }

  if (items.length === 0) return { element: null, consumed: 0 }

  return {
    element: (
      <ul key={`${keyPrefix}-subul`} className={`${ulClass} mt-1`}>
        {items}
      </ul>
    ),
    consumed: items.length,
  }
}

export default function parseGuideContent(content: string): React.ReactNode {
  const rawLines = content.split('\n')
  const parsed = rawLines.map(classifyLine)
  const elements: React.ReactNode[] = []
  let i = 0
  let key = 0

  while (i < parsed.length) {
    const line = parsed[i]!

    // Skip leading/trailing blanks at top level
    if (line.type === 'blank') {
      i++
      continue
    }

    // --- Section header ---
    if (line.type === 'header') {
      elements.push(
        <h3 key={`h-${key++}`} className={h3Class}>
          {renderInline(line.text, `h-${key}`)}
        </h3>
      )
      i++
      continue
    }

    // --- Numbered list ---
    if (line.type === 'numbered') {
      const items: React.ReactNode[] = []
      const listKey = key++
      while (i < parsed.length) {
        const cur = parsed[i]!
        if (cur.type === 'numbered' && cur.indent === line.indent) {
          const liKey = `ol-${listKey}-${items.length}`
          const liContent: React.ReactNode[] = [renderInline(cur.text, liKey)]
          i++
          // Gather indented sub-items (bullets or deeper numbered)
          const { element: subList, consumed } = buildSubItems(parsed, i, cur.indent, liKey)
          if (subList) {
            liContent.push(subList)
            i += consumed
          }
          items.push(
            <li key={liKey} className={liClass}>
              {liContent}
            </li>
          )
        } else if (cur.type === 'blank') {
          // Blank line might end the list or just be spacing within
          const next = parsed[i + 1]
          if (next && next.type === 'numbered' && next.indent === line.indent) {
            i++ // skip blank, continue list
          } else {
            break
          }
        } else if (cur.type === 'bullet' && cur.indent > line.indent) {
          // Sub-bullet under a numbered item that wasn't caught above
          const liKey = `ol-${listKey}-sub-${items.length}`
          const { element: subList, consumed } = buildSubItems(parsed, i, line.indent, liKey)
          if (subList && items.length > 0) {
            // Append to last li
            const lastItem = items[items.length - 1] as React.ReactElement
            items[items.length - 1] = React.cloneElement(lastItem, {}, lastItem.props.children, subList)
            i += consumed
          } else {
            break
          }
        } else if (cur.type === 'text' && cur.indent > line.indent) {
          // Indented text continuation under a numbered item
          if (items.length > 0) {
            const lastItem = items[items.length - 1] as React.ReactElement
            items[items.length - 1] = React.cloneElement(
              lastItem,
              {},
              lastItem.props.children,
              <br key={`br-${i}`} />,
              renderInline(cur.text, `ol-${listKey}-cont-${i}`)
            )
          }
          i++
        } else {
          break
        }
      }
      elements.push(
        <ol key={`ol-${listKey}`} className={olClass}>
          {items}
        </ol>
      )
      continue
    }

    // --- Bullet list ---
    if (line.type === 'bullet' && line.indent < 4) {
      const items: React.ReactNode[] = []
      const listKey = key++
      while (i < parsed.length) {
        const cur = parsed[i]!
        if (cur.type === 'bullet' && cur.indent === line.indent) {
          items.push(
            <li key={`ul-${listKey}-${items.length}`} className={liClass}>
              {renderInline(cur.text, `ul-${listKey}-${items.length}`)}
            </li>
          )
          i++
        } else if (cur.type === 'blank') {
          const next = parsed[i + 1]
          if (next && next.type === 'bullet' && next.indent === line.indent) {
            i++
          } else {
            break
          }
        } else {
          break
        }
      }
      elements.push(
        <ul key={`ul-${listKey}`} className={ulClass}>
          {items}
        </ul>
      )
      continue
    }

    // --- Regular text / indented bullets treated as text ---
    {
      const textLines: string[] = []
      const textKey = key++
      while (i < parsed.length) {
        const cur = parsed[i]!
        if (cur.type === 'text' || (cur.type === 'bullet' && cur.indent >= 4)) {
          textLines.push(cur.raw)
          i++
        } else {
          break
        }
      }
      if (textLines.length > 0) {
        elements.push(
          <p key={`p-${textKey}`} className={pClass}>
            {renderInline(textLines.join('\n'), `p-${textKey}`)}
          </p>
        )
      }
    }
  }

  return elements
}
