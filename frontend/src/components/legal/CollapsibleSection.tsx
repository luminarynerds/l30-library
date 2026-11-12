/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useId } from 'react'
import { ChevronDown } from 'lucide-react'

interface CollapsibleSectionProps {
  title: string
  children: React.ReactNode
  isOpen?: boolean
  onToggle?: (isOpen: boolean) => void
  className?: string
  badge?: string
}

export default function CollapsibleSection({
  title,
  children,
  isOpen = false,
  onToggle,
  className = '',
  badge,
}: CollapsibleSectionProps): React.ReactElement {
  const [internalOpen, setInternalOpen] = useState(isOpen)
  const contentId = useId()
  const isControlled = onToggle !== undefined
  const open = isControlled ? isOpen : internalOpen

  const handleToggle = () => {
    if (isControlled) {
      onToggle?.(!open)
    } else {
      setInternalOpen(!internalOpen)
    }
  }

  return (
    <div className={`border border-lsc-border dark:border-earth-700 rounded-lg overflow-hidden ${className}`}>
      <button
        onClick={handleToggle}
        className="w-full px-4 py-3 flex items-center justify-between gap-2 hover:bg-lsc-cream dark:hover:bg-earth-800/50 transition-colors text-left"
        aria-expanded={open}
        aria-controls={contentId}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <span className="font-medium text-lsc-dark dark:text-earth-50 truncate" title={title}>{title}</span>
          {badge && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0">
              {badge}
            </span>
          )}
        </div>
        <ChevronDown
          className={`w-5 h-5 text-lsc-dark dark:text-earth-50 flex-shrink-0 transition-transform ${
            open ? 'rotate-180' : ''
          }`}
          aria-hidden="true"
        />
      </button>

      {open && (
        <div id={contentId} className="px-4 py-3 border-t border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-900/20">
          {children}
        </div>
      )}
    </div>
  )
}
