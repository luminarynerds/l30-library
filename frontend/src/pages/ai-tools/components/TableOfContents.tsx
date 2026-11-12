/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { clsx } from '@/utils/helpers'
import { EASE_OUT_EXPO } from '../motion'

export interface TocEntry {
  id: string
  label: string
}

interface TableOfContentsProps {
  entries: TocEntry[]
}

export default function TableOfContents({ entries }: TableOfContentsProps): React.ReactElement {
  const [activeId, setActiveId] = useState<string>(entries[0]?.id ?? '')

  useEffect(() => {
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) return

    const targets = entries
      .map(e => document.getElementById(e.id))
      .filter((el): el is HTMLElement => el !== null)

    if (targets.length === 0) return

    const observer = new IntersectionObserver(
      observed => {
        const visible = observed
          .filter(entry => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActiveId(visible[0].target.id)
      },
      { rootMargin: '-20% 0px -70% 0px', threshold: 0 },
    )

    targets.forEach(t => observer.observe(t))
    return () => observer.disconnect()
  }, [entries])

  return (
    <>
      {/* Desktop: sticky right rail */}
      <nav
        aria-label="On this page"
        className="hidden lg:block sticky top-24 self-start max-h-[calc(100vh-8rem)] overflow-y-auto"
      >
        <p className="text-xs font-semibold uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          On this page
        </p>
        <ul className="space-y-1.5 border-l border-lsc-border dark:border-earth-700">
          {entries.map(entry => {
            const isActive = entry.id === activeId
            return (
              <li key={entry.id}>
                <a
                  href={`#${entry.id}`}
                  className={clsx(
                    '-ml-px block border-l-2 pl-3 py-1 text-sm transition-colors duration-300',
                    EASE_OUT_EXPO,
                    isActive
                      ? 'border-lsc-rose text-lsc-rose dark:text-lsc-rose-light font-semibold'
                      : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream',
                  )}
                >
                  {entry.label}
                </a>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Mobile: horizontal chip row, sticky under header */}
      <nav
        aria-label="On this page (contents)"
        className="lg:hidden sticky top-16 z-10 -mx-4 px-4 py-3 bg-lsc-cream/95 dark:bg-earth-900/95 backdrop-blur border-b border-lsc-border dark:border-earth-700"
      >
        <ul className="flex gap-2 overflow-x-auto no-scrollbar">
          {entries.map(entry => {
            const isActive = entry.id === activeId
            return (
              <li key={entry.id} className="flex-shrink-0">
                <a
                  href={`#${entry.id}`}
                  className={clsx(
                    'inline-block px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors duration-300',
                    EASE_OUT_EXPO,
                    isActive
                      ? 'bg-lsc-rose text-lsc-white'
                      : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-700',
                  )}
                >
                  {entry.label}
                </a>
              </li>
            )
          })}
        </ul>
      </nav>
    </>
  )
}
