/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import * as Sentry from '@/lib/sentry-lazy'
import toast from 'react-hot-toast'
import { Modal } from '@/components/ui/Modal'
import { useTranslation } from '@/i18n'
import {
  rescheduleConnectionGroupMeeting,
  type GroupMeeting,
  type ParentConnectionGroup,
} from '@/api/parent-onboarding-api'
import { Field, ModalFooter, REDACTED_CTX, inputCls } from './shared'

interface RescheduleProps {
  group: ParentConnectionGroup
  meeting: GroupMeeting
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function RescheduleMeetingDialog({
  group, meeting, isOpen, onClose, onSuccess,
}: RescheduleProps) {
  const { t } = useTranslation()
  const [newDate, setNewDate] = useState('')
  const [newTime, setNewTime] = useState(meeting.scheduled_time ?? '')
  const [newLocation, setNewLocation] = useState(meeting.location ?? '')
  const [notes, setNotes] = useState('')
  const [patronMessage, setPatronMessage] = useState('')

  useEffect(() => {
    if (!isOpen) {
      setNewDate('')
      setNewTime(meeting.scheduled_time ?? '')
      setNewLocation(meeting.location ?? '')
      setNotes('')
      setPatronMessage('')
    }
  }, [isOpen, meeting])

  const mutation = useMutation({
    mutationFn: () =>
      rescheduleConnectionGroupMeeting(group.id, meeting.id, {
        new_date: newDate,
        new_time: newTime || null,
        new_location: newLocation || null,
        notes: notes || undefined,
        patron_message: patronMessage || undefined,
      }),
    onSuccess: (res) => {
      const msg = res.email_partial
        ? t('parentOnboarding.connectionGroups.admin.meetings.reschedulePartial')
        : t('parentOnboarding.connectionGroups.admin.meetings.rescheduleSuccess', {
            count: String(res.notified_member_count ?? 0),
          })
      toast.success(msg)
      onSuccess()
    },
    onError: (err) => {
      Sentry.captureException(err, REDACTED_CTX)
      toast.error(t('parentOnboarding.connectionGroups.admin.meetings.rescheduleErrorGeneric'))
    },
  })

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('parentOnboarding.connectionGroups.admin.meetings.rescheduleTitle')}
      size="lg"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (!newDate) return
          mutation.mutate()
        }}
        className="space-y-4"
        data-testid="cg-reschedule-form"
      >
        <Field
          label={t('parentOnboarding.connectionGroups.admin.meetings.rescheduleNewDateLabel')}
          required
        >
          <input
            type="date"
            required
            value={newDate}
            onChange={(e) => setNewDate(e.target.value)}
            className={inputCls}
            data-testid="cg-reschedule-date"
          />
        </Field>
        <Field
          label={t('parentOnboarding.connectionGroups.admin.meetings.rescheduleNewTimeLabel')}
        >
          <input
            type="time"
            value={newTime}
            onChange={(e) => setNewTime(e.target.value)}
            className={inputCls}
          />
        </Field>
        <Field
          label={t('parentOnboarding.connectionGroups.admin.meetings.rescheduleNewLocationLabel')}
        >
          <input
            type="text"
            value={newLocation}
            onChange={(e) => setNewLocation(e.target.value)}
            maxLength={300}
            className={inputCls}
          />
        </Field>
        <Field label={t('parentOnboarding.connectionGroups.admin.meetings.cancelNotesLabel')}>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={2000}
            rows={2}
            className={inputCls}
          />
        </Field>
        <Field label={t('parentOnboarding.connectionGroups.admin.meetings.patronMessageLabel')}>
          <textarea
            value={patronMessage}
            onChange={(e) => setPatronMessage(e.target.value)}
            maxLength={500}
            rows={3}
            className={inputCls}
          />
        </Field>
        <ModalFooter
          onCancel={onClose}
          cancelLabel={t('parentOnboarding.connectionGroups.admin.meetings.cancelKeepOpen')}
          submitLabel={t('parentOnboarding.connectionGroups.admin.meetings.rescheduleSubmit')}
          submitting={mutation.isPending}
          submitDisabled={!newDate}
        />
      </form>
    </Modal>
  )
}
