/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Download, ExternalLink } from 'lucide-react'
import { API_BASE } from '@/api/types'
import type { Event } from '@/api/api'
import { downloadICalFeed } from '@/utils/calendarExport'
import { t } from '@/i18n'

interface CalendarExportMenuProps {
  events: Event[]
  onClose: () => void
}

const CalendarExportMenu = React.memo(function CalendarExportMenu({
  events,
  onClose,
}: CalendarExportMenuProps) {
  const menuRef = React.useRef<HTMLDivElement>(null)

  const handleExportAll = () => {
    downloadICalFeed(events, 'library-events.ics')
    onClose()
  }

  const handleCopySubscriptionUrl = () => {
    const subscriptionUrl = `${window.location.origin}${API_BASE}/events/calendar.ics`
    navigator.clipboard.writeText(subscriptionUrl)
    onClose()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    const items = menuRef.current?.querySelectorAll('[role="menuitem"]') as NodeListOf<HTMLElement> | undefined
    if (!items?.length) return

    const currentIndex = Array.from(items).indexOf(document.activeElement as HTMLElement)

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        items[(currentIndex + 1) % items.length]!.focus()
        break
      case 'ArrowUp':
        e.preventDefault()
        items[(currentIndex - 1 + items.length) % items.length]!.focus()
        break
      case 'Home':
        e.preventDefault()
        items[0]!.focus()
        break
      case 'End':
        e.preventDefault()
        items[items.length - 1]!.focus()
        break
      case 'Escape':
        e.preventDefault()
        onClose()
        break
    }
  }

  return (
    <div
      ref={menuRef}
      className="absolute right-0 top-full mt-1 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-2 z-20 min-w-[200px]"
      role="menu"
      aria-label={t('aria.eventCalendarView.calendarExportOptions')}
      onKeyDown={handleKeyDown}
    >
      <button
        onClick={handleExportAll}
        className="w-full text-left px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10"
        role="menuitem"
        tabIndex={-1}
      >
        <Download className="w-4 h-4" aria-hidden="true" />
        Download all events (.ics)
      </button>
      <button
        onClick={handleCopySubscriptionUrl}
        className="w-full text-left px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10"
        role="menuitem"
        tabIndex={-1}
      >
        <ExternalLink className="w-4 h-4" aria-hidden="true" />
        Copy subscription URL
      </button>
      <div className="border-t border-lsc-border dark:border-earth-700 my-1" role="separator" />
      <p className="px-3 py-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        Subscribe in Google Calendar or Outlook to stay updated
      </p>
    </div>
  )
})

export default CalendarExportMenu
