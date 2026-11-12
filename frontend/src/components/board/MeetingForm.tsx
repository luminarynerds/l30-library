/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useRef, useCallback, useEffect } from 'react'
import { X, Loader2 } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import type { BoardMeeting } from './MeetingsSection'
import { useTranslation} from '@/i18n'

export interface MeetingFormData {
  title: string
  description: string
  scheduled_date: string | undefined
  start_time: string
  end_time: string
  location: string
  agenda: string
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'cancelled'
}

interface MeetingFormProps {
  meeting?: BoardMeeting | null
  onSubmit: (data: MeetingFormData) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

export default function MeetingForm({
  meeting,
  onSubmit,
  onCancel,
  loading = false,
}: MeetingFormProps): React.ReactElement {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    title: meeting?.title || '',
    description: meeting?.description || '',
    scheduled_date: meeting
      ? new Date(meeting.scheduled_date).toISOString().split('T')[0]
      : new Date().toISOString().split('T')[0],
    start_time: meeting?.start_time || '09:00',
    end_time: meeting?.end_time || '10:00',
    location: meeting?.location || '',
    agenda: meeting?.agenda || '',
    status: meeting?.status || ('SCHEDULED' as const),
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const titleInputRef = useRef<HTMLInputElement>(null)

  // Handle Escape key
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && !loading && !submitting) {
      onCancel()
    }
  }, [loading, submitting, onCancel])

  // Focus title input when modal opens
  useEffect(() => {
    titleInputRef.current?.focus()
  }, [])

  const validate = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.title.trim()) {
      newErrors.title = 'Meeting title is required'
    }
    if (!formData.scheduled_date) {
      newErrors.scheduled_date = 'Date is required'
    }
    if (!formData.start_time) {
      newErrors.start_time = 'Start time is required'
    }
    if (formData.end_time && formData.start_time >= formData.end_time) {
      newErrors.end_time = 'End time must be after start time'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
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
      await onSubmit(formData)
    } finally {
      setSubmitting(false)
    }
  }

  const isLoading = submitting || loading

  const dialogTitleId = 'meeting-form-title'

  return (
    <FocusTrap
      focusTrapOptions={{
        initialFocus: () => titleInputRef.current,
        allowOutsideClick: true,
        escapeDeactivates: false,
        fallbackFocus: () => closeButtonRef.current || document.body,
        returnFocusOnDeactivate: true,
      }}
    >
      <div
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        role="presentation"
        onKeyDown={handleKeyDown}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={dialogTitleId}
          className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        >
          {/* Header */}
          <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 p-6 flex items-center justify-between">
            <h2
              id={dialogTitleId}
              className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream"
            >
              {meeting ? 'Edit Meeting' : 'Schedule Meeting'}
            </h2>
            <button
              ref={closeButtonRef}
              onClick={onCancel}
              disabled={isLoading}
              className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              aria-label={t('aria.board.closeMeetingForm')}
            >
              <X className="w-6 h-6 text-lsc-dark dark:text-lsc-cream" aria-hidden="true" />
            </button>
          </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Title */}
          <div>
            <label htmlFor="meeting-title" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Meeting Title <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
            </label>
            <input
              ref={titleInputRef}
              type="text"
              id="meeting-title"
              name="title"
              value={formData.title}
              onChange={handleChange}
              disabled={isLoading}
              aria-required="true"
              aria-invalid={!!errors.title}
              aria-describedby={errors.title ? 'meeting-title-error' : undefined}
              className={`w-full px-4 py-2 rounded-lg border ${
                errors.title
                  ? 'border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20'
                  : 'border-lsc-border dark:border-earth-700'
              } bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50`}
              placeholder={t('placeholder.board.boardMeetingJanuary2026')}
            />
            {errors.title && (
              <p id="meeting-title-error" role="alert" className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">{errors.title}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Description
            </label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              disabled={isLoading}
              rows={3}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
              placeholder={t('components.board.meetingForm.briefDescriptionOfTheMeeting')}
            />
          </div>

          {/* Date and Time */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label htmlFor="meeting-scheduled-date" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Date <span className="text-status-danger-600" aria-label={t('aria.addRoleModal.required')}>*</span>
              </label>
              <input
                type="date"
                id="meeting-scheduled-date"
                name="scheduled_date"
                value={formData.scheduled_date}
                onChange={handleChange}
                disabled={isLoading}
                min={!meeting ? new Date().toISOString().split('T')[0] : undefined}
                aria-required="true"
                aria-invalid={!!errors.scheduled_date}
                aria-describedby={errors.scheduled_date ? 'meeting-date-error' : 'meeting-date-hint'}
                className={`w-full px-4 py-2 rounded-lg border ${
                  errors.scheduled_date
                    ? 'border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20'
                    : 'border-lsc-border dark:border-earth-700'
                } bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50`}
              />
              <p id="meeting-date-hint" className="sr-only">{t('components.board.meetingForm.selectADateForThe')}</p>
              {errors.scheduled_date && (
                <p id="meeting-date-error" role="alert" className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">
                  {errors.scheduled_date}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Start Time *
              </label>
              <input
                type="time"
                name="start_time"
                value={formData.start_time}
                onChange={handleChange}
                disabled={isLoading}
                className={`w-full px-4 py-2 rounded-lg border ${
                  errors.start_time
                    ? 'border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20'
                    : 'border-lsc-border dark:border-earth-700'
                } bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50`}
              />
              {errors.start_time && (
                <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">{errors.start_time}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                End Time
              </label>
              <input
                type="time"
                name="end_time"
                value={formData.end_time}
                onChange={handleChange}
                disabled={isLoading}
                className={`w-full px-4 py-2 rounded-lg border ${
                  errors.end_time
                    ? 'border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20'
                    : 'border-lsc-border dark:border-earth-700'
                } bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50`}
              />
              {errors.end_time && (
                <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">{errors.end_time}</p>
              )}
            </div>
          </div>

          {/* Location */}
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Location
            </label>
            <input
              type="text"
              name="location"
              value={formData.location}
              onChange={handleChange}
              disabled={isLoading}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
              placeholder={t('components.board.meetingForm.conferenceRoomVirtualMeetingLink')}
            />
          </div>

          {/* Agenda */}
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Agenda
            </label>
            <textarea
              name="agenda"
              value={formData.agenda}
              onChange={handleChange}
              disabled={isLoading}
              rows={3}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
              placeholder={t('placeholder.board.1OpeningRemarks102Approval')}
            />
          </div>

          {/* Status */}
          {meeting && (
            <div>
              <label htmlFor="meeting-status" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Status
              </label>
              <select
                id="meeting-status"
                name="status"
                value={formData.status}
                onChange={handleChange}
                disabled={isLoading}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
              >
                <option value="SCHEDULED">Scheduled</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="COMPLETED">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          )}

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
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              {meeting ? 'Update Meeting' : 'Schedule Meeting'}
            </button>
          </div>
        </form>
        </div>
      </div>
    </FocusTrap>
  )
}
