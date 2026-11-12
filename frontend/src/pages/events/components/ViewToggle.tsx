/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef } from 'react'
import { Calendar, List, ChevronDown, CalendarDays, LayoutList, AlignJustify } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation } from '@/i18n/I18nContext'
import type { ViewMode } from '@/pages/events/utils/eventsPageUtils'

interface ViewToggleProps {
  viewMode: ViewMode
  onChange: (mode: ViewMode) => void
}

export default function ViewToggle({ viewMode, onChange }: ViewToggleProps): React.ReactElement {
  const { t } = useTranslation()
  const [showCalendarOptions, setShowCalendarOptions] = useState(false)
  const calendarMenuRef = useRef<HTMLDivElement>(null)
  const calendarTriggerRef = useRef<HTMLButtonElement>(null)

  const isCalendarView = viewMode === 'calendar-month' || viewMode === 'calendar-week'

  const handleCalendarMenuKeyDown = (e: React.KeyboardEvent) => {
    if (!showCalendarOptions) return

    const items = calendarMenuRef.current?.querySelectorAll('[role="menuitemradio"]') as NodeListOf<HTMLElement> | undefined
    if (!items?.length) return

    const currentIndex = Array.from(items).indexOf(document.activeElement as HTMLElement)

    switch (e.key) {
      case 'ArrowDown': {
        e.preventDefault()
        const nextItem = items[(currentIndex + 1) % items.length]
        nextItem?.focus()
        break
      }
      case 'ArrowUp': {
        e.preventDefault()
        const prevItem = items[(currentIndex - 1 + items.length) % items.length]
        prevItem?.focus()
        break
      }
      case 'Home': {
        e.preventDefault()
        const firstItem = items[0]
        firstItem?.focus()
        break
      }
      case 'End': {
        e.preventDefault()
        const lastItem = items[items.length - 1]
        lastItem?.focus()
        break
      }
      case 'Escape':
        e.preventDefault()
        setShowCalendarOptions(false)
        calendarTriggerRef.current?.focus()
        break
      case 'Tab':
        setShowCalendarOptions(false)
        break
    }
  }

  const buttonBaseClass =
    'flex items-center gap-2 px-3 sm:px-4 py-2 min-h-[44px] rounded-xl text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose shadow-sm hover:shadow touch-manipulation'
    const activeClass = 'bg-lsc-dark dark:bg-lsc-cream text-white dark:text-lsc-dark font-semibold'
  const inactiveClass =
    'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-border dark:hover:bg-lsc-brown/90 border-2 border-lsc-border dark:border-lsc-brown'

  return (
    <div className="flex gap-2" role="group" aria-label={t('events.viewMode')}>
      {/* List View */}
      <button
        onClick={() => onChange('list')}
        className={clsx(buttonBaseClass, viewMode === 'list' ? activeClass : inactiveClass)}
        aria-pressed={viewMode === 'list'}
        aria-label={t('events.listView')}
      >
        <List className="w-4 h-4" aria-hidden="true" />
        <span className="hidden sm:inline">{t('events.list')}</span>
      </button>

      {/* Calendar View with dropdown */}
      <div className="relative" onKeyDown={handleCalendarMenuKeyDown}>
        <button
          ref={calendarTriggerRef}
          onClick={() => {
            if (isCalendarView) {
              setShowCalendarOptions(!showCalendarOptions)
            } else {
              onChange('calendar-month')
              setShowCalendarOptions(false)
            }
          }}
          className={clsx(buttonBaseClass, isCalendarView ? activeClass : inactiveClass)}
          aria-pressed={isCalendarView}
          aria-haspopup={isCalendarView ? 'menu' : undefined}
          aria-expanded={showCalendarOptions}
          aria-label={t('events.calendarView')}
        >
          <Calendar className="w-4 h-4" aria-hidden="true" />
          <span className="hidden sm:inline">
            {viewMode === 'calendar-week' ? t('events.week') : t('events.month')}
          </span>
          {isCalendarView && <ChevronDown className="w-3 h-3 ml-0.5" aria-hidden="true" />}
        </button>

        {showCalendarOptions && isCalendarView && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setShowCalendarOptions(false)}
              aria-hidden="true"
            />
            <div
              ref={calendarMenuRef}
              className="absolute right-0 top-full mt-1 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-1 z-20 min-w-[140px]"
              role="menu"
              aria-label={t('events.calendarViewOptions')}
            >
              <button
                onClick={() => {
                  onChange('calendar-month')
                  setShowCalendarOptions(false)
                }}
                className={clsx(
                  'w-full text-left px-3 py-2 text-sm rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10',
                  viewMode === 'calendar-month'
                    ? 'bg-lsc-rose/10 text-lsc-rose dark:text-lsc-rose-light font-medium'
                    : 'text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown'
                )}
                role="menuitemradio"
                tabIndex={-1}
                aria-checked={viewMode === 'calendar-month'}
              >
                <CalendarDays className="w-4 h-4" aria-hidden="true" />
                {t('events.monthView')}
              </button>
              <button
                onClick={() => {
                  onChange('calendar-week')
                  setShowCalendarOptions(false)
                }}
                className={clsx(
                  'w-full text-left px-3 py-2 text-sm rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10',
                  viewMode === 'calendar-week'
                    ? 'bg-lsc-rose/10 text-lsc-rose dark:text-lsc-rose-light font-medium'
                    : 'text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown'
                )}
                role="menuitemradio"
                tabIndex={-1}
                aria-checked={viewMode === 'calendar-week'}
              >
                <Calendar className="w-4 h-4" aria-hidden="true" />
                {t('events.weekView')}
              </button>
            </div>
          </>
        )}
      </div>

      {/* Agenda View */}
      <button
        onClick={() => onChange('agenda')}
        className={clsx(buttonBaseClass, viewMode === 'agenda' ? activeClass : inactiveClass)}
        aria-pressed={viewMode === 'agenda'}
        aria-label={t('events.agendaView')}
      >
        <LayoutList className="w-4 h-4" aria-hidden="true" />
        <span className="hidden sm:inline">{t('events.agendaLabel')}</span>
      </button>

      {/* Linear View — flat chronological list, promotional rails suppressed */}
      <button
        onClick={() => onChange('linear')}
        className={clsx(buttonBaseClass, viewMode === 'linear' ? activeClass : inactiveClass)}
        aria-pressed={viewMode === 'linear'}
        aria-label={t('events.linearView')}
      >
        <AlignJustify className="w-4 h-4" aria-hidden="true" />
        <span className="hidden sm:inline">{t('events.linear')}</span>
      </button>
    </div>
  )
}
