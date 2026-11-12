/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import * as Sentry from '@/lib/sentry-lazy'
import toast from 'react-hot-toast'
import { Modal } from '@/components/ui/Modal'
import { useTranslation } from '@/i18n'
import {
  archiveConnectionGroup,
  type ArchiveReason,
  type ParentConnectionGroup,
} from '@/api/parent-onboarding-api'
import { Field, ModalFooter, REDACTED_CTX, inputCls } from './shared'

const ARCHIVE_REASONS: ArchiveReason[] = [
  'cohort_complete', 'low_attendance', 'facilitator_departed', 'other',
]

interface ArchiveProps {
  group: ParentConnectionGroup
  isOpen: boolean
  onClose: () => void
}

export function ArchiveGroupDialog({ group, isOpen, onClose }: ArchiveProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [reason, setReason] = useState<ArchiveReason>('cohort_complete')
  const [notes, setNotes] = useState('')
  const [notify, setNotify] = useState(false)
  const [patronMessage, setPatronMessage] = useState('')

  useEffect(() => {
    if (!isOpen) {
      setReason('cohort_complete')
      setNotes('')
      setNotify(false)
      setPatronMessage('')
    }
  }, [isOpen])

  const mutation = useMutation({
    mutationFn: () =>
      archiveConnectionGroup(group.id, {
        archive_reason: reason,
        archive_notes: notes || undefined,
        notify_members: notify,
        patron_message: patronMessage || undefined,
      }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['connection-groups'] })
      if (res.email_dispatched && (res.notified_member_count ?? 0) > 0) {
        toast.success(
          t('parentOnboarding.connectionGroups.admin.archive.successNotified', {
            count: String(res.notified_member_count ?? 0),
          }),
        )
      } else {
        toast.success(t('parentOnboarding.connectionGroups.admin.archive.success'))
      }
      onClose()
    },
    onError: (err) => {
      Sentry.captureException(err, REDACTED_CTX)
      toast.error(t('parentOnboarding.connectionGroups.admin.archive.errorGeneric'))
    },
  })

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('parentOnboarding.connectionGroups.admin.archive.title', { groupName: group.name })}
      size="lg"
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
        className="space-y-4"
        data-testid="cg-archive-form"
      >
        <Field
          label={t('parentOnboarding.connectionGroups.admin.archive.reasonLabel')}
          required
        >
          <select
            value={reason}
            onChange={(e) => setReason(e.target.value as ArchiveReason)}
            className={inputCls}
            data-testid="cg-archive-reason"
          >
            {ARCHIVE_REASONS.map((r) => (
              <option key={r} value={r}>
                {t(`parentOnboarding.connectionGroups.admin.archive.reason.${r}`)}
              </option>
            ))}
          </select>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {t('parentOnboarding.connectionGroups.admin.archive.reasonHint')}
          </p>
        </Field>

        <Field label={t('parentOnboarding.connectionGroups.admin.archive.notesLabel')}>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={2000}
            rows={3}
            className={inputCls}
          />
        </Field>

        <label className="inline-flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={notify}
            onChange={(e) => setNotify(e.target.checked)}
            data-testid="cg-archive-notify-toggle"
          />
          {t('parentOnboarding.connectionGroups.admin.archive.notifyToggle')}
        </label>
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 -mt-2">
          {t('parentOnboarding.connectionGroups.admin.archive.notifyHint')}
        </p>

        {notify && (
          <Field label={t('parentOnboarding.connectionGroups.admin.archive.patronMessageLabel')}>
            <textarea
              value={patronMessage}
              onChange={(e) => setPatronMessage(e.target.value)}
              maxLength={2000}
              rows={4}
              className={inputCls}
              data-testid="cg-archive-patron-message"
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {t('parentOnboarding.connectionGroups.admin.archive.patronMessageHint')}
            </p>
          </Field>
        )}

        <ModalFooter
          onCancel={onClose}
          cancelLabel={t('parentOnboarding.connectionGroups.admin.archive.cancel')}
          submitLabel={t('parentOnboarding.connectionGroups.admin.archive.submit')}
          submitting={mutation.isPending}
        />
      </form>
    </Modal>
  )
}
