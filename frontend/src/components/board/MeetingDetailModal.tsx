/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useEffect } from 'react'
import FocusTrap from 'focus-trap-react'
import { X, Calendar, Clock, MapPin, FileText, Edit2 } from 'lucide-react'
import type { BoardMeeting } from './MeetingsSection'
import { getCurrentLocale } from '@/i18n'

interface MeetingDetailModalProps {
  meeting: BoardMeeting
  onClose: () => void
  onEdit?: () => void
  userRole: string
}

export default function MeetingDetailModal({
  meeting,
  onClose,
  onEdit,
  userRole,
}: MeetingDetailModalProps): React.ReactElement {
  const isAdmin = ['admin', 'super_admin'].includes(userRole)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: true }}>
    <div role="dialog" aria-modal="true" aria-labelledby="meeting-detail-modal-title" className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 p-6 flex items-center justify-between">
          <h2 id="meeting-detail-modal-title" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Meeting Details
          </h2>
          <button
            onClick={onClose}
            aria-label="Close meeting details"
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-lsc-dark dark:text-lsc-cream" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Title and Status */}
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                {meeting.title}
              </h3>
              <span
                className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                  meeting.status
                )}`}
              >
                {meeting.status?.replace('_', ' ') ?? 'unknown'}
              </span>
            </div>
            {meeting.description && (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{meeting.description}</p>
            )}
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="w-5 h-5 text-lsc-rose" />
                <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                  Date
                </span>
              </div>
              <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                {new Date(meeting.scheduled_date).toLocaleDateString(getCurrentLocale(), {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </div>

            <div className="p-4 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-5 h-5 text-lsc-rose" />
                <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                  Time
                </span>
              </div>
              <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                {meeting.start_time}
                {meeting.end_time && ` - ${meeting.end_time}`}
              </p>
            </div>
          </div>

          {/* Location */}
          {meeting.location && (
            <div className="p-4 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <MapPin className="w-5 h-5 text-lsc-rose" />
                <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                  Location
                </span>
              </div>
              <p className="text-lsc-dark dark:text-lsc-cream">{meeting.location}</p>
            </div>
          )}

          {/* Agenda */}
          {meeting.agenda && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <FileText className="w-5 h-5 text-lsc-rose" />
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">Agenda</span>
              </div>
              <div className="p-4 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
                <p className="text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">
                  {meeting.agenda}
                </p>
              </div>
            </div>
          )}

          {/* Additional Info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-lsc-border dark:border-earth-700">
            {meeting.attendees && (
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Attendees
                </p>
                <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                  {meeting.attendees}
                </p>
              </div>
            )}
            {meeting.meeting_minutes_id && (
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Meeting Minutes
                </p>
                <span className="inline-block px-3 py-1 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 rounded-full text-sm font-medium">
                  Published
                </span>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors font-medium"
            >
              Close
            </button>
            {isAdmin && onEdit && (
              <button
                onClick={onEdit}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors"
              >
                <Edit2 className="w-4 h-4" />
                Edit
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
    </FocusTrap>
  )
}

function getStatusColor(status: string) {
  switch (status) {
    case 'COMPLETED':
      return 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
    case 'IN_PROGRESS':
      return 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light'
    case 'SCHEDULED':
      return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
    case 'cancelled':
      return 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300'
    default:
      return 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'
  }
}
