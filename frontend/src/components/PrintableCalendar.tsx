/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo, useRef, useEffect } from 'react'
import FocusTrap from 'focus-trap-react'
import { Printer, X, Calendar } from 'lucide-react'
import type { Event } from '@/api/api'
import { useBranding } from '@/contexts/BrandingContext'
import { t, getCurrentLocale } from '@/i18n'

interface PrintableCalendarProps {
  events: Event[]
  isOpen: boolean
  onClose: () => void
  month?: Date
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleTimeString(getCurrentLocale(), {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString(getCurrentLocale(), {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  })
}

export default function PrintableCalendar({
  events,
  isOpen,
  onClose,
  month = new Date()
}: PrintableCalendarProps): React.ReactElement | null {
  const branding = useBranding()
  const printRef = useRef<HTMLDivElement>(null)

  const year = month.getFullYear()
  const monthIndex = month.getMonth()
  const monthName = month.toLocaleDateString(getCurrentLocale(), { month: 'long', year: 'numeric' })
  const firstDay = new Date(year, monthIndex, 1)
  const lastDay = new Date(year, monthIndex + 1, 0)
  const daysInMonth = lastDay.getDate()
  const startingDayOfWeek = firstDay.getDay()

  // Group events by day
  const eventsByDay = useMemo(() =>
    events.reduce((acc, event) => {
      const eventDate = new Date(event.start_time)
      if (eventDate.getFullYear() === year && eventDate.getMonth() === monthIndex) {
        const day = eventDate.getDate()
        if (!acc[day]) acc[day] = []
        acc[day].push(event)
      }
      return acc
    }, {} as Record<number, Event[]>),
    [events, year, monthIndex]
  )

  // Sort events within each day by time
  const sortedEventsByDay = useMemo(() => {
    const sorted: Record<number, Event[]> = {}
    Object.keys(eventsByDay).forEach(day => {
      sorted[Number(day)] = [...(eventsByDay[Number(day)] || [])].sort(
        (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
      )
    })
    return sorted
  }, [eventsByDay])

  // List view events sorted by date
  const sortedEvents = useMemo(() =>
    [...events]
      .filter(event => {
        const eventDate = new Date(event.start_time)
        return eventDate.getFullYear() === year && eventDate.getMonth() === monthIndex
      })
      .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()),
    [events, year, monthIndex]
  )

  const handlePrint = () => {
    window.print()
  }

  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  if (!isOpen) return null

  // Generate calendar grid
  const calendarCells = []
  for (let i = 0; i < startingDayOfWeek; i++) {
    calendarCells.push(
      <td key={`empty-${i}`} className="print-calendar-cell empty" />
    )
  }
  for (let day = 1; day <= daysInMonth; day++) {
    const dayEvents = sortedEventsByDay[day] || []
    calendarCells.push(
      <td key={day} className="print-calendar-cell">
        <div className="print-day-number">{day}</div>
        {dayEvents.map(event => (
          <div key={event.id} className="print-event">
            <span className="print-event-time">{formatTime(event.start_time)}</span>
            <span className="print-event-title">{event.title}</span>
          </div>
        ))}
      </td>
    )
  }

  // Arrange cells into rows
  const calendarRows = []
  for (let i = 0; i < calendarCells.length; i += 7) {
    calendarRows.push(
      <tr key={i}>
        {calendarCells.slice(i, i + 7)}
      </tr>
    )
  }

  return (
    <>
      {/* Print styles injected via style tag */}
      <style>{`
        @media print {
          /* Hide everything except the print container */
          body * {
            visibility: hidden;
          }
          .print-container,
          .print-container * {
            visibility: visible;
          }
          .print-container {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            padding: 0.5in;
            background: white !important;
            color: black !important;
          }
          .no-print {
            display: none !important;
          }

          /* Page setup */
          @page {
            size: letter portrait;
            margin: 0.5in;
          }

          /* Calendar table */
          .print-calendar-table {
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
            page-break-inside: avoid;
          }
          .print-calendar-table th,
          .print-calendar-table td {
            border: 1px solid #333;
            padding: 4px;
            vertical-align: top;
            font-size: 10pt;
            color: black !important;
            background: white !important;
          }
          .print-calendar-table th {
            background: #f0f0f0 !important;
            font-weight: bold;
            text-align: center;
            padding: 8px 4px;
          }
          .print-calendar-cell {
            height: 80px;
            min-height: 80px;
            page-break-inside: avoid;
          }
          .print-calendar-cell.empty {
            background: #fafafa !important;
          }
          .print-day-number {
            font-weight: bold;
            font-size: 12pt;
            margin-bottom: 4px;
            color: black !important;
          }
          .print-event {
            font-size: 8pt;
            margin-bottom: 2px;
            line-height: 1.2;
            color: black !important;
          }
          .print-event-time {
            font-weight: 600;
            margin-right: 4px;
          }
          .print-event-title {
            display: inline;
          }

          /* Header */
          .print-header {
            text-align: center;
            margin-bottom: 16px;
          }
          .print-header h1 {
            font-size: 18pt;
            margin: 0 0 4px 0;
            color: black !important;
          }
          .print-header p {
            font-size: 10pt;
            color: #666 !important;
            margin: 0;
          }

          /* Event list section - new page */
          .print-list-section {
            page-break-before: always;
            margin-top: 24px;
          }
          .print-list-section h2 {
            font-size: 14pt;
            margin-bottom: 12px;
            border-bottom: 2px solid #333;
            padding-bottom: 4px;
            page-break-after: avoid;
            color: black !important;
          }

          /* Individual event items - keep together */
          .print-list-item {
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid #ddd;
            page-break-inside: avoid;
          }
          .print-list-item:last-child {
            border-bottom: none;
          }
          .print-list-date {
            font-weight: bold;
            font-size: 11pt;
            color: black !important;
          }
          .print-list-title {
            font-size: 12pt;
            font-weight: 600;
            margin: 4px 0;
            color: black !important;
          }
          .print-list-details {
            font-size: 10pt;
            color: #444 !important;
          }
          .print-list-details span {
            margin-right: 16px;
          }

          /* Footer */
          .print-footer {
            margin-top: 24px;
            text-align: center;
            font-size: 9pt;
            color: #666 !important;
            border-top: 1px solid #ddd;
            padding-top: 8px;
          }

          /* Orphans and widows for long event lists */
          p, li {
            orphans: 3;
            widows: 3;
          }
        }
      `}</style>

      {/* Modal overlay */}
      <FocusTrap active={isOpen} focusTrapOptions={{ escapeDeactivates: true }}>
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 no-print"
        onClick={onClose}
        role="dialog"
        aria-modal="true"
        aria-labelledby="print-dialog-title"
      >
        <div
          className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-auto shadow-lg"
          onClick={e => e.stopPropagation()}
          tabIndex={0}
          onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); } }}
          role="button"
        >
          {/* Modal header */}
          <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 p-4 flex items-center justify-between z-10 no-print">
            <div className="flex items-center gap-3">
              <Calendar className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
              <h2 id="print-dialog-title" className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Print Monthly Calendar
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handlePrint}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
              >
                <Printer className="w-4 h-4" aria-hidden="true" />
                Print
              </button>
              <button
                onClick={onClose}
                className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                aria-label={t('aria.printableCalendar.closePrintPreview')}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Print preview content */}
          <div ref={printRef} className="print-container p-6 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream">
            {/* Header */}
            <div className="print-header">
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream print:text-black">
                {monthName} Events
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 print:text-earth-600">
                {branding.library_name}
              </p>
            </div>

            {/* Calendar grid */}
            <table className="print-calendar-table w-full border-collapse mt-4">
              <thead>
                <tr>
                  {['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map(day => (
                    <th
                      key={day}
                      className="border border-lsc-border dark:border-earth-700 bg-lsc-cream dark:bg-earth-700 p-2 text-center text-sm font-semibold text-lsc-dark dark:text-lsc-cream print:bg-earth-100 print:text-black"
                    >
                      {day}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {calendarRows}
              </tbody>
            </table>

            {/* Detailed event list */}
            <div className="print-list-section mt-8">
              <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream border-b-2 border-lsc-rose pb-2 mb-4 print:text-black print:border-black">
                Event Details
              </h2>
              {sortedEvents.length === 0 ? (
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 print:text-earth-600">
                  No events scheduled for this month.
                </p>
              ) : (
                <div className="space-y-4">
                  {sortedEvents.map(event => (
                    <div
                      key={event.id}
                      className="print-list-item border-b border-lsc-border dark:border-earth-700 pb-4 last:border-b-0 print:border-lsc-border"
                    >
                      <div className="print-list-date text-sm text-lsc-rose dark:text-lsc-rose-light font-semibold print:text-earth-700">
                        {formatDate(event.start_time)}
                      </div>
                      <div className="print-list-title text-lg font-semibold text-lsc-dark dark:text-lsc-cream print:text-black">
                        {event.title}
                      </div>
                      <div className="print-list-details text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 flex flex-wrap gap-4 print:text-earth-600">
                        <span>
                          <strong>Time:</strong> {formatTime(event.start_time)}
                          {event.end_time && ` - ${formatTime(event.end_time)}`}
                        </span>
                        {event.location && (
                          <span>
                            <strong>Location:</strong> {event.location}
                          </span>
                        )}
                        {event.audience && (
                          <span>
                            <strong>Audience:</strong> {event.audience}
                          </span>
                        )}
                        {event.category && (
                          <span>
                            <strong>Category:</strong> {event.category}
                          </span>
                        )}
                      </div>
                      {event.description && (
                        <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mt-2 print:text-earth-700">
                          {event.description}
                        </p>
                      )}
                      {event.registration_required && (
                        <p className="text-sm text-lsc-rose dark:text-lsc-rose-light mt-2 font-medium print:text-earth-800">
                          Registration required
                          {event.max_attendees && ` (${event.max_attendees} spots)`}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="print-footer mt-8 pt-4 border-t border-lsc-border dark:border-earth-700 text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70 print:border-lsc-border print:text-earth-600">
              <p>
                {branding.library_name} | {branding.phone} | {branding.contact_email}
              </p>
              <p className="mt-1">
                Printed on {new Date().toLocaleDateString(getCurrentLocale(), { month: 'long', day: 'numeric', year: 'numeric' })}
              </p>
            </div>
          </div>
        </div>
      </div>
      </FocusTrap>
    </>
  )
}
