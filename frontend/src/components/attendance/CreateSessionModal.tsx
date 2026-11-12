/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import FocusTrap from 'focus-trap-react'
import { useMutation } from '@tanstack/react-query'
import { X, Plus, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { createAttendanceSession, type AttendanceSession } from '../../api/attendance-api'
import { useTranslation } from '@/i18n'
import { t } from '@/i18n'

interface CreateSessionModalProps {
  onClose: () => void
  onCreated: (session: AttendanceSession) => void
}

export function CreateSessionModal({
  onClose,
  onCreated,
}: CreateSessionModalProps) {
  const [name, setName] = useState('')
  const [sessionDate, setSessionDate] = useState(new Date().toISOString().split('T')[0] ?? '')
  const [headCountMode, setHeadCountMode] = useState(false)
  const [eventCost, setEventCost] = useState('')
  const [surveyEnabled, setSurveyEnabled] = useState(true)
  const [surveyLink, setSurveyLink] = useState('')
  const { t: tHook } = useTranslation()

  const createMutation = useMutation({
    mutationFn: createAttendanceSession,
    onSuccess: (session) => {
      toast.success(t('toast.attendanceTracking.sessionCreated'))
      onCreated(session)
    },
    onError: (err: Error) => toast.error(err.message || t('toast.attendanceTracking.failedToCreateSession')),
  })

  return (

    // eslint-disable-next-line jsx-a11y/click-events-have-key-events
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: true }}>
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div
        role="dialog" aria-modal="true" aria-labelledby="attendance-session-title" className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-lg mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 id="attendance-session-title" className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">New Attendance Session</h2>
          <button onClick={onClose} className="text-earth-600 dark:text-earth-600 hover:text-earth-600 dark:hover:text-earth-300">
            <X size={20} />
          </button>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate({
              session_name: name,
              session_date: sessionDate,
              head_count_mode: headCountMode,
              event_cost: eventCost ? parseFloat(eventCost) : null,
              survey_enabled: surveyEnabled,
              survey_link: surveyLink || null,
            })
          }}
          className="space-y-4"
        >
          <div>
            <label htmlFor="session-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Session Name *</label>
            <input
              id="session-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={tHook('placeholder.attendanceTracking.egSummerReadingKickoff')}
              required
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg text-sm bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </div>

          <div>
            <label htmlFor="session-date" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Date *</label>
            <input
              id="session-date"
              type="date"
              value={sessionDate}
              onChange={(e) => setSessionDate(e.target.value)}
              required
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg text-sm bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </div>

          <div>
            <label htmlFor="session-event-cost" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Event Cost (for ROI tracking)
            </label>
            <input
              id="session-event-cost"
              type="number"
              value={eventCost}
              onChange={(e) => setEventCost(e.target.value)}
              placeholder={tHook('placeholder.staff.000')}
              min="0"
              step="0.01"
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg text-sm bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <input
                type="checkbox"
                checked={headCountMode}
                onChange={(e) => setHeadCountMode(e.target.checked)}
                className="rounded"
              />
              Head count mode (large events)
            </label>
            <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <input
                type="checkbox"
                checked={surveyEnabled}
                onChange={(e) => setSurveyEnabled(e.target.checked)}
                className="rounded"
              />
              Enable post-event survey
            </label>
          </div>

          {surveyEnabled && (
            <div>
              <label htmlFor="session-survey-link" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Survey Link</label>
              <input
                id="session-survey-link"
                type="url"
                value={surveyLink}
                onChange={(e) => setSurveyLink(e.target.value)}
                placeholder={tHook('placeholder.attendanceTracking.httpsformsexamplecomsurvey')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg text-sm bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || createMutation.isPending}
              className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-1"
            >
              {createMutation.isPending ? <Loader2 size={14} className="motion-safe:animate-spin" /> : <Plus size={14} />}
              Create Session
            </button>
          </div>
        </form>
      </div>
      </FocusTrap>
    </div>
  )
}
