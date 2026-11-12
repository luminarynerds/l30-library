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
  cancelConnectionGroupMeeting,
  type CancelMeetingReason,
  type GroupMeeting,
  type ParentConnectionGroup,
} from '@/api/parent-onboarding-api'
import { Field, ModalFooter, REDACTED_CTX, inputCls } from './shared'

const CANCEL_REASONS: CancelMeetingReason[] = [
  'facilitator_sick', 'venue_unavailable', 'weather', 'low_rsvp', 'other',
]

interface CancelProps {
  group: ParentConnectionGroup
  meeting: GroupMeeting
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function CancelMeetingDialog({
  group, meeting, isOpen, onClose, onSuccess,
}: CancelProps) {
  const { t } = useTranslation()
  const [reason, setReason] = useState<CancelMeetingReason>('facilitator_sick')
  const [notes, setNotes] = useState('')
  const [patronMessage, setPatronMessage] = useState('')

  useEffect(() => {
    if (!isOpen) {
      setReason('facilitator_sick')
      setNotes('')
      setPatronMessage('')
    }
  }, [isOpen])

  const mutation = useMutation({
    mutationFn: () =>
      cancelConnectionGroupMeeting(group.id, meeting.id, {
        reason,
        notes: notes || undefined,
        patron_message: patronMessage || undefined,
      }),
    onSuccess: (res) => {
      const msg = res.email_partial
        ? t('parentOnboarding.connectionGroups.admin.meetings.cancelPartial')
        : t('parentOnboarding.connectionGroups.admin.meetings.cancelSuccess', {
            count: String(res.notified_member_count ?? 0),
          })
      toast.success(msg)
      onSuccess()
    },
    onError: (err) => {
      Sentry.captureException(err, REDACTED_CTX)
      toast.error(t('parentOnboarding.connectionGroups.admin.meetings.cancelErrorGeneric'))
    },
  })

  // role=alertdialog: cancellation is irreversible AND emails go out.
  // We intentionally override Modal's role via the wrapping div + don't
  // rely on Modal's role="dialog" for this case. Modal still owns focus
  // trapping.
  const preview = patronMessage
    ? patronMessage
    : t('parentOnboarding.connectionGroups.admin.meetings.previewBodyDefault', {
        groupName: group.name,
        date: meeting.meeting_date,
      })

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('parentOnboarding.connectionGroups.admin.meetings.cancelTitle')}
      size="lg"
    >
      <div role="alertdialog" aria-live="polite" data-testid="cg-cancel-meeting-dialog">
        <p className="text-sm mb-4">
          {t('parentOnboarding.connectionGroups.admin.meetings.cancelConfirm')}
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            mutation.mutate()
          }}
          className="space-y-4"
        >
          <Field
            label={t('parentOnboarding.connectionGroups.admin.meetings.cancelReasonLabel')}
            required
          >
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value as CancelMeetingReason)}
              className={inputCls}
              data-testid="cg-cancel-reason"
            >
              {CANCEL_REASONS.map((r) => (
                <option key={r} value={r}>
                  {t(`parentOnboarding.connectionGroups.admin.meetings.reason.${r}`)}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('parentOnboarding.connectionGroups.admin.meetings.cancelNotesLabel')}>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={2000}
              rows={2}
              className={inputCls}
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {t('parentOnboarding.connectionGroups.admin.meetings.cancelNotesHint')}
            </p>
          </Field>

          <Field label={t('parentOnboarding.connectionGroups.admin.meetings.patronMessageLabel')}>
            <textarea
              value={patronMessage}
              onChange={(e) => setPatronMessage(e.target.value)}
              maxLength={500}
              rows={3}
              className={inputCls}
              data-testid="cg-cancel-patron-message"
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {t('parentOnboarding.connectionGroups.admin.meetings.patronMessageHint')}
            </p>
          </Field>

          <div className="bg-lsc-cream/40 dark:bg-earth-800/60 rounded-lg p-3">
            <p className="text-xs font-semibold uppercase text-lsc-dark/60 dark:text-lsc-cream/60 mb-1">
              {t('parentOnboarding.connectionGroups.admin.meetings.previewHeading')}
            </p>
            <p
              className="text-sm whitespace-pre-wrap"
              data-testid="cg-cancel-preview"
            >
              {preview}
            </p>
          </div>

          <ModalFooter
            onCancel={onClose}
            cancelLabel={t('parentOnboarding.connectionGroups.admin.meetings.cancelKeepOpen')}
            submitLabel={t('parentOnboarding.connectionGroups.admin.meetings.cancelSubmit')}
            submitting={mutation.isPending}
            destructive
          />
        </form>
      </div>
    </Modal>
  )
}
