/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect, useId } from 'react'
import { HelpCircle } from 'lucide-react'

interface GlossaryTermLinkProps {
  term: string
  definition: string
  children?: React.ReactNode
  className?: string
}

export default function GlossaryTermLink({
  term,
  definition,
  children,
  className = '',
}: GlossaryTermLinkProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [position, setPosition] = useState<'top' | 'bottom'>('bottom')
  const triggerRef = useRef<HTMLButtonElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const tooltipId = useId()

  useEffect(() => {
    if (isOpen && triggerRef.current && popoverRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect()
      const popoverRect = popoverRef.current.getBoundingClientRect()

      // Check if there's enough space below
      if (triggerRect.bottom + popoverRect.height + 10 > window.innerHeight) {

        setPosition('top')
      } else {
        setPosition('bottom')
      }
    }
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false)
        triggerRef.current?.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  return (
    <div className="relative inline-block">
      <button
        type="button"
        ref={triggerRef}
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setIsOpen(false)}
        onClick={() => setIsOpen(!isOpen)}
        aria-describedby={isOpen ? tooltipId : undefined}
        className={`inline-flex items-center gap-1 text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium cursor-help ${className}`}
      >
        {children || term}
        <HelpCircle className="w-3 h-3 flex-shrink-0" aria-hidden="true" />
      </button>

      {isOpen && (
        <div
          id={tooltipId}
          ref={popoverRef}
          role="tooltip"
          className={`absolute z-50 w-64 p-3 bg-lsc-dark dark:bg-earth-900 text-lsc-cream dark:text-earth-50 rounded-lg shadow-lg border border-lsc-rose/20 ${
            position === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'
          } left-1/2 -translate-x-1/2 text-sm`}
        >
          <div className="font-semibold text-lsc-rose dark:text-lsc-rose-light mb-1">
            {term}
          </div>
          <p className="text-xs leading-relaxed">{definition}</p>
          {/* Arrow pointer */}
          <div
            className={`absolute w-2 h-2 bg-lsc-dark dark:bg-earth-900 border border-lsc-rose/20 transform rotate-45 ${
              position === 'top' ? 'bottom-[-5px]' : 'top-[-5px]'
            } left-1/2 -translate-x-1/2`}
          />
        </div>
      )}
    </div>
  )
}
