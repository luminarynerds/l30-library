/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useRef, useEffect } from 'react'
import { X, Loader2 } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { attendeeName, type MeetingMinutes, type BoardMeeting, type MinutesFormData } from './MinutesSection'
import { useTranslation} from '@/i18n'

interface MinutesFormProps {
  minutes?: MeetingMinutes | null
  meetings: BoardMeeting[]
  onSubmit: (data: MinutesFormData) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

export default function MinutesForm({
  minutes,
  meetings,
  onSubmit,
  onCancel,
  loading = false,
}: MinutesFormProps): React.ReactElement {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    meeting_id: minutes?.meeting_id || '',
    status: minutes?.status || 'not_started',
    notes: minutes?.notes || '',
    members_present: minutes?.members_present || [],
    members_absent: minutes?.members_absent || [],
    guests_present: minutes?.guests_present || [],
    quorum_met: minutes?.quorum_met ?? true,
    quorum_count: minutes?.quorum_count || '',
  })

  const [membersPresentText, setMembersPresentText] = useState(
    (minutes?.members_present || []).map(attendeeName).join('\n')
  )
  const [membersAbsentText, setMembersAbsentText] = useState(
    (minutes?.members_absent || []).map(attendeeName).join('\n')
  )
  const [guestsPresentText, setGuestsPresentText] = useState(
    (minutes?.guests_present || []).map(attendeeName).join('\n')
  )

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const firstInputRef = useRef<HTMLSelectElement>(null)

  // Handle Escape key via global listener
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !loading && !submitting) {
        onCancel()
      }
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [loading, submitting, onCancel])

  // Focus first input when modal opens
  useEffect(() => {
    firstInputRef.current?.focus()
  }, [])

  const validate = () => {
    const newErrors: Record<string, string> = {}

    if (!minutes && !formData.meeting_id) {
      newErrors.meeting_id = 'Please select a meeting'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target
    const newValue = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    setFormData((prev) => ({ ...prev, [name]: newValue }))
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[name]
        return newErrors
      })
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) return

    try {
      setSubmitting(true)
      // Parse text areas into arrays
      const submitData = {
        ...formData,
        members_present: membersPresentText.split('\n').filter(s => s.trim()),
        members_absent: membersAbsentText.split('\n').filter(s => s.trim()),
        guests_present: guestsPresentText.split('\n').filter(s => s.trim()),
      }
      await onSubmit(submitData)
    } finally {
      setSubmitting(false)
    }
  }

  const isLoading = submitting || loading
  const dialogTitleId = 'minutes-form-title'

  return (
    <FocusTrap
      focusTrapOptions={{
        initialFocus: () => firstInputRef.current,
        allowOutsideClick: true,
        escapeDeactivates: false,
        fallbackFocus: () => closeButtonRef.current || document.body,
        returnFocusOnDeactivate: true,
      }}
    >
      <div
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        role="presentation"

      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={dialogTitleId}
          className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto"
        >
          {/* Header */}
          <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 p-6 flex items-center justify-between">
            <h2
              id={dialogTitleId}
              className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream"
            >
              {minutes ? 'Edit Meeting Minutes' : 'Create Meeting Minutes'}
            </h2>
            <button
              ref={closeButtonRef}
              onClick={onCancel}
              disabled={isLoading}
              className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              aria-label={t('aria.board.closeForm')}
            >
              <X className="w-6 h-6 text-lsc-dark dark:text-lsc-cream" aria-hidden="true" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* Meeting Selection */}
            {!minutes && (
              <div>
                <label htmlFor="minutes-meeting-id" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Meeting <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
                </label>
                <select
                  ref={firstInputRef}
                  id="minutes-meeting-id"
                  name="meeting_id"
                  value={formData.meeting_id}
                  onChange={handleChange}
                  disabled={isLoading}
                  aria-required="true"
                  aria-invalid={!!errors.meeting_id}
                  aria-describedby={errors.meeting_id ? 'meeting-id-error' : undefined}
                  className={`w-full px-4 py-2 rounded-lg border ${
                    errors.meeting_id
                      ? 'border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20'
                      : 'border-lsc-border dark:border-earth-700'
                  } bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50`}
                >
                  <option value="">Select a meeting...</option>
                  {meetings.map((meeting) => (
                    <option key={meeting.id} value={meeting.id}>
                      {meeting.title} - {new Date(meeting.scheduled_date).toLocaleDateString()}
                    </option>
                  ))}
                </select>
                {errors.meeting_id && (
                  <p id="meeting-id-error" role="alert" className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">{errors.meeting_id}</p>
                )}
              </div>
            )}

            {/* Status */}
            <div>
              <label htmlFor="minutes-status" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Status
              </label>
              <select
                id="minutes-status"
                name="status"
                value={formData.status}
                onChange={handleChange}
                disabled={isLoading}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
              >
                <option value="not_started">Not Started</option>
                <option value="in_progress">In Progress</option>
                <option value="draft">Draft</option>
                <option value="ready_for_review">Ready for Review</option>
              </select>
            </div>

            {/* Quorum */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="quorum_met"
                  name="quorum_met"
                  checked={formData.quorum_met}
                  onChange={handleChange}
                  disabled={isLoading}
                  className="w-4 h-4 text-lsc-rose rounded focus:ring-lsc-rose"
                />
                <label htmlFor="quorum_met" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  Quorum Met
                </label>
              </div>
              <div>
                <label htmlFor="quorum-count" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Quorum Count
                </label>
                <input
                  type="text"
                  id="quorum-count"
                  name="quorum_count"
                  value={formData.quorum_count}
                  onChange={handleChange}
                  disabled={isLoading}
                  className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
                  placeholder={t('placeholder.board.eg5Of7')}
                />
              </div>
            </div>

            {/* Members Present */}
            <div>
              <label htmlFor="members-present" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Members Present (one per line)
              </label>
              <textarea
                id="members-present"
                value={membersPresentText}
                onChange={(e) => setMembersPresentText(e.target.value)}
                disabled={isLoading}
                rows={4}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
                placeholder={t('components.board.minutesForm.johnSmithJaneDoeBob')}
              />
            </div>

            {/* Members Absent */}
            <div>
              <label htmlFor="members-absent" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Members Absent (one per line)
              </label>
              <textarea
                id="members-absent"
                value={membersAbsentText}
                onChange={(e) => setMembersAbsentText(e.target.value)}
                disabled={isLoading}
                rows={3}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
                placeholder={t('components.board.minutesForm.listAnyAbsentMembers')}
              />
            </div>

            {/* Guests Present */}
            <div>
              <label htmlFor="guests-present" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Guests Present (one per line)
              </label>
              <textarea
                id="guests-present"
                value={guestsPresentText}
                onChange={(e) => setGuestsPresentText(e.target.value)}
                disabled={isLoading}
                rows={3}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
                placeholder={t('placeholder.board.listAnyGuests')}
              />
            </div>

            {/* Notes */}
            <div>
              <label htmlFor="minutes-notes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Notes
              </label>
              <textarea
                id="minutes-notes"
                name="notes"
                value={formData.notes}
                onChange={handleChange}
                disabled={isLoading}
                rows={6}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
                placeholder={t('components.board.minutesForm.generalNotesAboutTheMeeting')}
              />
            </div>

            {/* Buttons */}
            <div className="flex gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
              <button
                type="button"
                onClick={onCancel}
                disabled={isLoading}
                className="flex-1 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors disabled:opacity-50 font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                aria-busy={isLoading}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />}
                {minutes ? 'Update Minutes' : 'Create Minutes'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </FocusTrap>
  )
}
