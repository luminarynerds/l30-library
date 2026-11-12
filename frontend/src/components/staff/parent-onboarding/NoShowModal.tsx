/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useId, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import toast from 'react-hot-toast'
import * as Sentry from "@/lib/sentry-lazy"
import {
  updateChildcareRegistration,
  type ChildcareRegistration,
} from '@/api/parent-onboarding-api'
import { useTranslation } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

export function NoShowModal({
  registration,
  onClose,
}: {
  registration: ChildcareRegistration
  onClose: () => void
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const headingId = useId()
  const reasonId = useId()
  const [reason, setReason] = useState('')

  const mutation = useMutation({
    mutationFn: () =>
      updateChildcareRegistration(registration.id, {
        status: 'no_show',
        ...(reason.trim() && { no_show_reason: reason.trim().slice(0, 500) }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['childcare-roster', registration.session_id] })
      queryClient.invalidateQueries({ queryKey: ['childcare-sessions'] })
      toast.success(t('parentOnboarding.childcare.roster.noShowConfirmed'))
      onClose()
    },
    onError: (err) => {
      Sentry.captureException(err)
      toast.error(t('parentOnboarding.childcare.roster.noShowError'))
    },
  })

  return (
    <ModalBackdrop onClose={onClose} labelledBy={headingId}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-3">
          <h2
            id={headingId}
            className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
          >
            {t('parentOnboarding.childcare.noShowModal.heading', { name: registration.child_name })}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={t('aria.authModals.close')}
            className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
          >
            <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" aria-hidden="true" />
          </button>
        </div>
        <div>
          <label htmlFor={reasonId} className="block text-sm font-medium mb-1">
            {t('parentOnboarding.childcare.noShowModal.reasonLabel')}
          </label>
          <textarea
            id={reasonId}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={500}
            rows={3}
            className="w-full text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          />
        </div>
        <div className="flex gap-2 justify-end mt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-2 text-sm border border-lsc-border dark:border-earth-600 rounded-lg"
          >
            {t('parentOnboarding.childcare.noShowModal.cancel')}
          </button>
          <button
            type="button"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            data-testid="no-show-confirm"
            className="px-3 py-2 text-sm bg-status-danger-700 text-white rounded-lg disabled:opacity-50"
          >
            {t('parentOnboarding.childcare.noShowModal.confirm')}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
