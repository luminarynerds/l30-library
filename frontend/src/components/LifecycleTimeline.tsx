/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import {
  Package,
  PackageCheck,
  FileText,
  CheckCircle,
  PlusCircle,
  BookOpen,
  ArrowUpFromLine,
  RefreshCw,
  Bookmark,
  Wrench,
  AlertTriangle,
  Settings,
  Clipboard,
  HelpCircle,
  Search,
  Tag,
  Check,
  X,
  Recycle,
  Trash2,
  MapPin,
  ArrowLeftRight,
  Pin,
  FileQuestion,
  type LucideIcon,
} from 'lucide-react'
import { LifecycleEvent, LifecycleEventType } from '../api/api'
import { useTranslation, getCurrentLocale } from '@/i18n'

interface LifecycleTimelineProps {
  events: LifecycleEvent[]
  loading?: boolean
}

const eventTypeLabels: Record<LifecycleEventType, string> = {
  ordered: 'Ordered',
  received: 'Received',
  cataloging_started: 'Cataloging Started',
  cataloged: 'Cataloged',
  copy_created: 'Copy Created',
  shelved: 'Shelved',
  checked_out: 'Checked Out',
  returned: 'Returned',
  renewed: 'Renewed',
  hold_placed: 'Hold Placed',
  hold_filled: 'Hold Filled',
  condition_changed: 'Condition Changed',
  damaged: 'Damaged',
  repaired: 'Repaired',
  inventoried: 'Inventoried',
  missing: 'Missing',
  found: 'Found',
  marked_for_weeding: 'Marked for Weeding',
  weeding_approved: 'Weeding Approved',
  weeding_rejected: 'Weeding Rejected',
  weeded: 'Weeded',
  disposed: 'Disposed',
  location_changed: 'Location Changed',
  transferred: 'Transferred',
  note_added: 'Note Added',
  selected: 'Selected',
  selection_approved: 'Selection Approved',
  patron_requested: 'Patron Requested',
  other: 'Other',
}

const eventTypeColors: Record<LifecycleEventType, string> = {
  ordered: 'bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light',
  received: 'bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light',
  cataloging_started: 'bg-category-100 dark:bg-category-900/30 text-category-800 dark:text-category-300',
  cataloged: 'bg-category-100 dark:bg-category-900/30 text-category-800 dark:text-category-300',
  copy_created: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300',
  shelved: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300',
  checked_out: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300',
  returned: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300',
  renewed: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300',
  hold_placed: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300',
  hold_filled: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300',
  condition_changed: 'bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100',
  damaged: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300',
  repaired: 'bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light',
  inventoried: 'bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light',
  missing: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300',
  found: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300',
  marked_for_weeding: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300',
  weeding_approved: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300',
  weeding_rejected: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300',
  weeded: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300',
  disposed: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300',
  location_changed: 'bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100',
  transferred: 'bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100',
  note_added: 'bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100',
  selected: 'bg-status-info-100 dark:bg-status-info-900/30 text-status-info-800 dark:text-status-info-300',
  selection_approved: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300',
  patron_requested: 'bg-category-100 dark:bg-category-900/30 text-category-800 dark:text-category-300',
  other: 'bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100',
}

const eventTypeIcons: Record<LifecycleEventType, LucideIcon> = {
  ordered: Package,
  received: PackageCheck,
  cataloging_started: FileText,
  cataloged: CheckCircle,
  copy_created: PlusCircle,
  shelved: BookOpen,
  checked_out: ArrowUpFromLine,
  returned: PackageCheck,
  renewed: RefreshCw,
  hold_placed: Bookmark,
  hold_filled: CheckCircle,
  condition_changed: Wrench,
  damaged: AlertTriangle,
  repaired: Settings,
  inventoried: Clipboard,
  missing: HelpCircle,
  found: Search,
  marked_for_weeding: Tag,
  weeding_approved: Check,
  weeding_rejected: X,
  weeded: Recycle,
  disposed: Trash2,
  location_changed: MapPin,
  transferred: ArrowLeftRight,
  note_added: Pin,
  selected: Check,
  selection_approved: CheckCircle,
  patron_requested: Bookmark,
  other: FileQuestion,
}

export function LifecycleTimeline({ events, loading = false }: LifecycleTimelineProps) {
  const { t } = useTranslation()
  const [expandedEvents, setExpandedEvents] = useState<Set<number>>(new Set())

  const toggleEvent = (eventId: number) => {
    setExpandedEvents(prev => {
      const newSet = new Set(prev)
      if (newSet.has(eventId)) {
        newSet.delete(eventId)
      } else {
        newSet.add(eventId)
      }
      return newSet
    })
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString(getCurrentLocale(), {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="motion-safe:animate-pulse space-y-4">
        <div className="h-20 bg-earth-200 dark:bg-earth-600 rounded"></div>
        <div className="h-20 bg-earth-200 dark:bg-earth-600 rounded"></div>
        <div className="h-20 bg-earth-200 dark:bg-earth-600 rounded"></div>
      </div>
    )
  }

  if (!events || events.length === 0) {
    return (
      <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
        <p>{t('components.lifecycleTimeline.noLifecycleEventsRecordedYet')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
        Item Lifecycle History ({events.length} event{events.length !== 1 ? 's' : ''})
      </h3>

      <div className="relative border-l-2 border-lsc-border dark:border-earth-700 pl-6 space-y-6">
        {events.map((event, _index) => {
          const isExpanded = expandedEvents.has(event.id)
          const hasMetadata = event.metadata && Object.keys(event.metadata).length > 0

          return (
            <div key={event.id} className="relative">
              {/* Timeline dot */}
              <div className="absolute -left-[1.6rem] top-1 w-6 h-6 rounded-full bg-lsc-white dark:bg-earth-800 border-2 border-earth-400 dark:border-earth-700 flex items-center justify-center">
                {(() => {
                  const IconComponent = eventTypeIcons[event.event_type]
                  return <IconComponent className="w-3 h-3" aria-hidden="true" />
                })()}
              </div>

              {/* Event card */}
              <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${eventTypeColors[event.event_type]}`}>
                        {eventTypeLabels[event.event_type]}
                      </span>
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        {formatDate(event.created_at)}
                      </span>
                    </div>

                    {event.description && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{event.description}</p>
                    )}

                    {event.performed_by_name && (
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        By: {event.performed_by_name}
                      </p>
                    )}
                  </div>

                  {hasMetadata && (
                    <button
                      onClick={() => toggleEvent(event.id)}
                      className="ml-4 text-sm text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light dark:hover:text-lsc-rose"
                    >
                      {isExpanded ? 'Hide details' : 'Show details'}
                    </button>
                  )}
                </div>

                {/* Expanded metadata */}
                {isExpanded && hasMetadata && (
                  <div className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700">
                    <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Details:</p>
                    <div className="bg-earth-50 dark:bg-earth-900 rounded p-2">
                      <pre className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 overflow-x-auto">
                        {JSON.stringify(event.metadata, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
