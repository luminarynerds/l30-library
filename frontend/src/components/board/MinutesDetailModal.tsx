/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Download, Printer } from 'lucide-react'
import { attendeeName, type MeetingMinutes } from './MinutesSection'
import { Modal } from '../ui/Modal'
import { openDownloadInNewTab } from '@/utils/openDownload'

interface MinutesDetailModalProps {
  minutes: MeetingMinutes
  onClose: () => void
}

export default function MinutesDetailModal({
  minutes,
  onClose,
}: MinutesDetailModalProps): React.ReactElement {
  const handlePrint = () => {
    window.print()
  }

  const handleDownload = () => {
    const title = minutes.meeting_title || `Meeting #${minutes.meeting_id}`
    const attendees = minutes.members_present?.map(attendeeName).filter(Boolean).join(', ') || 'N/A'
    const content = `
${title}
Meeting Date: ${minutes.meeting_date ? new Date(minutes.meeting_date).toLocaleDateString() : 'N/A'}
Status: ${minutes.approved ? 'Approved' : 'Draft'}
Attendees: ${attendees}

MEETING MINUTES
===============
${minutes.notes || 'No notes recorded'}

Generated on: ${new Date().toLocaleDateString()}
    `.trim()

    openDownloadInNewTab(
      'data:text/plain;charset=utf-8,' + encodeURIComponent(content),
      `${title.replace(/[^a-zA-Z0-9_-]/g, '_')}.txt`,
    )
  }

  const modalTitle = minutes.meeting_title || `Meeting #${minutes.meeting_id} Minutes`

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={modalTitle}
      size="2xl"
    >
      {/* Status badge */}
      <div className="mb-4">
        <span
          className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(minutes.approved)}`}
        >
          {minutes.approved ? 'Approved' : 'Draft'}
        </span>
      </div>

      {/* Content */}
      <div className="space-y-6">
          {/* Metadata */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
            {minutes.meeting_title && (
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Meeting
                </p>
                <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                  {minutes.meeting_title}
                </p>
              </div>
            )}
            {minutes.meeting_date && (
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Date
                </p>
                <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                  {new Date(minutes.meeting_date).toLocaleDateString()}
                </p>
              </div>
            )}
            {minutes.members_present && minutes.members_present.length > 0 && (
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Attendees
                </p>
                <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                  {minutes.members_present.map(attendeeName).filter(Boolean).join(', ')}
                </p>
              </div>
            )}
          </div>

          {/* Plain Language Summary */}
          {minutes.plain_language_summary && (
            <div className="bg-lsc-cream dark:bg-earth-700 rounded-xl p-4 border-l-4 border-lsc-rose">
              <h4 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">What This Means</h4>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{minutes.plain_language_summary}</p>
            </div>
          )}

          {/* Minutes Content */}
          <div>
            <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-3">
              Meeting Notes
            </h3>
            <div className="p-4 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
              <p className="text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap font-mono text-sm leading-relaxed">
                {minutes.notes || 'No notes recorded'}
              </p>
            </div>
          </div>

          {/* Sections */}
          {minutes.sections && minutes.sections.length > 0 && (
            <div>
              <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-3">
                Meeting Sections
              </h3>
              <div className="space-y-3">
                {minutes.sections.map((section, index) => (
                  <div key={section.id ?? `section-${section.title}-${index}`} className="p-4 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                      {section.title || `Section ${index + 1}`}
                    </p>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                      {section.content || section.notes || 'No content'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Document Info */}
          <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 pt-4 border-t border-lsc-border dark:border-earth-700">
            <p>Created: {new Date(minutes.created_at).toLocaleDateString()}</p>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors font-medium"
            >
              Close
            </button>
            <button
              onClick={handleDownload}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light hover:bg-earth-200 dark:hover:bg-earth-800/50 rounded-lg font-medium transition-colors"
            >
              <Download className="w-4 h-4" />
              Download
            </button>
            <button
              onClick={handlePrint}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors"
            >
              <Printer className="w-4 h-4" />
              Print
            </button>
          </div>
      </div>
    </Modal>
  )
}

function getStatusColor(approved: boolean | undefined) {
  if (approved) return 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300';
  return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300';
}
