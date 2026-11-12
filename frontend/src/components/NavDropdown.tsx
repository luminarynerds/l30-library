/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect, useCallback, useMemo, useId } from 'react'
import { createPortal } from 'react-dom'
import { Link, useLocation } from 'react-router-dom'
import { ChevronDown } from 'lucide-react'
import { clsx } from '@/utils/helpers'

type IconComponent = React.ElementType

interface NavItem {
  to: string
  label: string
  icon: IconComponent
  description?: string
  exact?: boolean
  /** W3C aria-keyshortcuts value, e.g. "g c" (announce-only; binding lives in Layout.tsx). */
  shortcut?: string
}

interface NavSection {
  heading: string
  items: NavItem[]
}

interface NavDropdownProps {
  label: string
  icon: IconComponent
  /** Flat list of items (simple dropdown) */
  items?: NavItem[]
  /** Grouped sections (mega-menu panel) */
  sections?: NavSection[]
  isActive: (path: string, exact?: boolean) => boolean
  /** Align dropdown panel: 'left' | 'right' | 'center' */
  align?: 'left' | 'right' | 'center'
}


export default function NavDropdown({
  label,
  icon: Icon,
  items = [],
  sections,
  isActive,
  align = 'left',
}: NavDropdownProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const panelId = useId()
  const triggerId = useId()
  // Tracks whether the panel was just opened so the focus effect can run once.
  const justOpenedRef = useRef(false)
  // When we close via Escape or Tab-out, we want to return focus to the trigger.
  // Click-outside should NOT steal focus back to the trigger.
  const returnFocusOnCloseRef = useRef(false)
  const location = useLocation()

  // Flatten sections into a single items list (used for active-state + count).
  const allItems = useMemo(() => {
    if (sections) {
      return sections.flatMap(section => section.items)
    }
    return items
  }, [sections, items])

  // Check if any child is active
  const hasActiveChild = useMemo(
    () => allItems.some(item => isActive(item.to, item.exact)),
    [isActive, allItems]
  )

  // Close on route change
  useEffect(() => {
    Promise.resolve().then(() => {
      setIsOpen(false)
    })
  }, [location.pathname])

  // Close on click outside (check both the trigger wrapper and the portal panel)
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node
      const inTrigger = dropdownRef.current?.contains(target)
      const inPanel = panelRef.current?.contains(target)
      if (!inTrigger && !inPanel) {
        returnFocusOnCloseRef.current = false
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  // Helper: focus the link at a wrapped index inside the panel.
  const focusLinkAt = useCallback((index: number) => {
    if (!panelRef.current) return
    const links = panelRef.current.querySelectorAll<HTMLAnchorElement>('a[href]')
    if (links.length === 0) return
    const wrapped = ((index % links.length) + links.length) % links.length
    links[wrapped]?.focus()
  }, [])

  // Keyboard handling on the trigger + panel container.
  // Disclosure semantics: Tab moves naturally through links. Esc closes and
  // returns focus to the trigger. ↑/↓ are a courtesy that moves DOM focus
  // among the links (not via aria-activedescendant).
  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Escape') {
      if (isOpen) {
        event.preventDefault()
        returnFocusOnCloseRef.current = true
        setIsOpen(false)
      }
      return
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (!isOpen) {
        setIsOpen(true)
        // Focus first link after panel opens (see opening effect below).
        justOpenedRef.current = true
      } else {
        // Move focus to next link relative to currently-focused link.
        if (!panelRef.current) return
        const links = Array.from(
          panelRef.current.querySelectorAll<HTMLAnchorElement>('a[href]')
        )
        const currentIdx = links.findIndex(l => l === document.activeElement)
        focusLinkAt(currentIdx === -1 ? 0 : currentIdx + 1)
      }
      return
    }

    if (event.key === 'ArrowUp' && isOpen) {
      event.preventDefault()
      if (!panelRef.current) return
      const links = Array.from(
        panelRef.current.querySelectorAll<HTMLAnchorElement>('a[href]')
      )
      const currentIdx = links.findIndex(l => l === document.activeElement)
      focusLinkAt(currentIdx === -1 ? links.length - 1 : currentIdx - 1)
      return
    }

    if (event.key === 'Home' && isOpen) {
      event.preventDefault()
      focusLinkAt(0)
      return
    }

    if (event.key === 'End' && isOpen) {
      event.preventDefault()
      const links = panelRef.current?.querySelectorAll('a[href]')
      if (links && links.length > 0) focusLinkAt(links.length - 1)
      return
    }
  }, [isOpen, focusLinkAt])

  // Track dropdown position for portal rendering
  const [menuPos, setMenuPos] = useState<{ top: number; left: number; width: number; viewportWidth: number }>({ top: 0, left: 0, width: 0, viewportWidth: window.innerWidth })

  const updateMenuPos = useCallback(() => {
    if (buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect()
      setMenuPos({ top: rect.bottom + 8, left: rect.left, width: rect.width, viewportWidth: window.innerWidth })
    }
  }, [])

  const toggleDropdown = () => {
    if (!isOpen) {
      updateMenuPos()
    }
    setIsOpen(prev => !prev)
  }

  // Reposition on scroll/resize while open
  useEffect(() => {
    if (!isOpen) return
    const handleReposition = () => updateMenuPos()
    window.addEventListener('scroll', handleReposition, true)
    window.addEventListener('resize', handleReposition)
    return () => {
      window.removeEventListener('scroll', handleReposition, true)
      window.removeEventListener('resize', handleReposition)
    }
  }, [isOpen, updateMenuPos])

  // On open via keyboard (ArrowDown), move focus to first link.
  useEffect(() => {
    if (isOpen && justOpenedRef.current) {
      justOpenedRef.current = false
      // Defer so portal panel is in the DOM.
      const id = window.setTimeout(() => focusLinkAt(0), 0)
      return () => window.clearTimeout(id)
    }
  }, [isOpen, focusLinkAt])

  // On close, optionally return focus to the trigger (Esc, route change, etc.).
  useEffect(() => {
    if (!isOpen && returnFocusOnCloseRef.current) {
      returnFocusOnCloseRef.current = false
      buttonRef.current?.focus()
    }
  }, [isOpen])

  const handleItemClick = () => {
    setIsOpen(false)
  }

  // Compute left position for the fixed portal based on alignment
  const getMenuStyle = useCallback((): React.CSSProperties => {
    const style: React.CSSProperties = { position: 'fixed', top: menuPos.top, zIndex: 9999 }
    if (align === 'right') {
      style.right = menuPos.viewportWidth - menuPos.left - menuPos.width
    } else if (align === 'center') {
      style.left = menuPos.left + menuPos.width / 2
      style.transform = 'translateX(-50%)'
    } else {
      style.left = menuPos.left
    }
    return style
  }, [menuPos, align])

  const hasSections = sections && sections.length > 0
  const isMegaMenu = hasSections

  const renderItem = (item: NavItem) => {
    const ItemIcon = item.icon
    return (
      <li key={item.to}>
        <Link
          to={item.to}
          className={clsx(
            'flex items-start gap-3 px-4 py-3 text-sm transition-colors rounded-lg mx-1',
            'focus-visible:outline-none focus-visible:bg-lsc-rose/10',
            isActive(item.to, item.exact)
              ? 'nav-active bg-lsc-rose/10 text-lsc-rose font-medium'
              : 'text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10'
          )}
          aria-current={isActive(item.to, item.exact) ? 'page' : undefined}
          aria-keyshortcuts={item.shortcut || undefined}
          onClick={handleItemClick}
        >
          <ItemIcon aria-hidden="true" className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="min-w-0">
            <span className="block font-medium leading-tight">{item.label}</span>
            {item.description && (
              <span className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5 leading-snug">
                {item.description}
              </span>
            )}
          </div>
        </Link>
      </li>
    )
  }

  const renderSections = () =>
    sections!.map((section, idx) => {
      const headingId = `${panelId}-section-${idx}-heading`
      return (
        <div key={section.heading} className="py-2">
          <div className="px-4 pb-1">
            <h3
              id={headingId}
              className="m-0 text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70"
            >
              {section.heading}
            </h3>
          </div>
          <ul aria-labelledby={headingId}>
            {section.items.map((item) => renderItem(item))}
          </ul>
        </div>
      )
    })

  return (
    <div ref={dropdownRef} className="relative" onKeyDown={handleKeyDown}>
      <button
        type="button"
        id={triggerId}
        ref={buttonRef}
        onClick={toggleDropdown}
        className={clsx(
          'flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium motion-safe:transition-all',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose',
          hasActiveChild
            ? 'nav-active bg-lsc-rose/10 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light font-bold'
            : 'text-earth-700 dark:text-earth-300 hover:bg-earth-50 dark:hover:bg-earth-800/15 hover:text-earth-950 dark:hover:text-lsc-cream'
        )}
        aria-expanded={isOpen}
        aria-controls={panelId}
        aria-haspopup="true"
      >
        <Icon aria-hidden="true" className="w-5 h-5" />
        {label}
        <ChevronDown
          aria-hidden="true"
          strokeWidth={2.5}
          className={clsx(
            'w-3.5 h-3.5 text-earth-700 dark:text-earth-300',
            'motion-safe:transition-transform motion-safe:duration-200',
            isOpen && 'rotate-180'
          )}
        />
      </button>

      {isOpen && createPortal(
        <div
          id={panelId}
          ref={panelRef}
          aria-labelledby={triggerId}
          style={getMenuStyle()}
          className={clsx(
            'bg-lsc-white dark:bg-earth-800 ring-1 ring-black/5 dark:ring-white/10 rounded-xl shadow-soft-xl dark:shadow-[0_8px_30px_rgba(0,0,0,0.6)] border border-lsc-border dark:border-earth-400/50 overflow-y-auto max-h-[calc(100vh-120px)]',
            isMegaMenu
              ? 'min-w-[280px] max-w-[calc(100vw-2rem)] sm:max-w-[420px] py-1'
              : 'min-w-[200px] max-w-[calc(100vw-2rem)] sm:max-w-[320px] py-1',
            'motion-safe:animate-menu-enter'
          )}
        >
          <span className="sr-only">{`${label}, ${allItems.length} items`}</span>
          {hasSections ? (
            renderSections()
          ) : (
            <ul>
              {allItems.map((item) => renderItem(item))}
            </ul>
          )}
        </div>,
        document.body
      )}
    </div>
  )
}
