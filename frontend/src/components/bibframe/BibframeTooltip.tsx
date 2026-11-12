/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect } from 'react'
import { HelpCircle } from 'lucide-react'

export function BibframeTooltip({ term, definition }: { term: string; definition: string }): React.ReactElement {
  const [open, setOpen] = useState(false)
  const tooltipRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (tooltipRef.current && !tooltipRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  return (
    <span className="relative inline-flex items-center gap-1" ref={tooltipRef}>
      <span className="font-semibold">{term}</span>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light focus:outline-none focus:ring-1 focus:ring-lsc-rose rounded"
        aria-label={`What is a ${term}?`}
        aria-expanded={open}
      >
        <HelpCircle className="w-3.5 h-3.5" aria-hidden="true" />
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 rounded-lg bg-lsc-dark dark:bg-earth-700 text-lsc-cream text-xs p-3 shadow-lg z-50 leading-relaxed"
        >
          {definition}
        </span>
      )}
    </span>
  )
}
