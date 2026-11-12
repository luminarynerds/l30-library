/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState, useId } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Check, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { placeHold, type CatalogItem } from '@/api/api'
import { listBranches } from '@/api/branch-api'
import { useAuth } from '@/contexts/AuthContext'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import { formatItemType } from './ItemOverview'
import { HoldQueueInfo } from './HoldQueueInfo'
import { useRelatedFormats } from '../hooks/useRelatedFormats'
import { Button } from '@/components/ui/Button'
import { friendlyErrorMessage } from '@/utils/friendlyError'
import { ApiError } from '@/lib/api-client'
import { useJourneyTracker } from '@/hooks/useJourneyTracker'
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { statusLabelI18n } from '../utils/catalogHelpers'

interface PlaceHoldModalProps {
  item: CatalogItem
  onClose: () => void
  onSuccess: () => void
}

export function PlaceHoldModal({
  item,
  onClose,
  onSuccess,
}: PlaceHoldModalProps): React.ReactElement {
  const { explicitConfirmations, announceToScreenReader } = useUnifiedAccessibility()
  const { trackStage } = useJourneyTracker({ journeyType: 'search_to_hold' })
  const { formats } = useRelatedFormats(item)
  const [selectedItemId, setSelectedItemId] = useState(item.id)
  const [selectedBranchId, setSelectedBranchId] = useState<number | undefined>(undefined)
  const [mutationError, setMutationError] = useState('')
  const mutationErrorRef = useRef<HTMLParagraphElement>(null)
  const holdErrorId = useId()

  useEffect(() => {
    if (mutationError && mutationErrorRef.current) {
      mutationErrorRef.current.focus()
    }
  }, [mutationError])

  // Reset selected item if the modal item changes
  // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional reset of selected format when a different item is shown
  useEffect(() => setSelectedItemId(item.id), [item.id])

  const { data: branches } = useQuery({
    queryKey: ['branches-pickup'],
    queryFn: () => listBranches({ active_only: true }),
    staleTime: 300_000,
  })

  // Track hold initiation
  useEffect(() => {
    trackStage('hold_initiated')
  }, [item.id, trackStage])

  const { token } = useAuth()

  const mutation = useMutation({
    mutationFn: () => placeHold(token!, selectedItemId, selectedBranchId),
    onSuccess: () => {
      trackStage('hold_placed')
      toast.success(t('toast.indie.holdPlacedSuccessfully'))
      announceToScreenReader(t('catalog.placeHoldModal.holdPlacedAnnouncement'))
      onSuccess()
      onClose()
    },
    onError: (error: Error) => {
      trackStage('hold_initiated', undefined, 'HOLD_FAILED')
      // The circulation API turns patron-safe business-rule details into Errors
      // (for example, a card-expiry or fine restriction returned as 403). Keep
      // those explanations visible instead of collapsing them into a generic
      // fallback. Raw ApiErrors remain supported for direct callers/tests.
      const msg =
        error instanceof ApiError && error.status === 422 && error.detail
          ? error.detail
          : error instanceof Error && !(error instanceof ApiError) && error.message
            ? error.message
          : friendlyErrorMessage(error)
      setMutationError(msg)
      toast.error(msg)
      announceToScreenReader(t('catalog.placeHoldModal.holdFailedAnnouncement'))
    },
  })

  return (
    <ModalBackdrop onClose={onClose} title={t('catalog.placeHold')}>
      <div
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-6"
      >
        <h2 id="hold-modal-title" className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
          {t('catalog.placeHold')}
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('catalog.placeHoldModal.prompt', { title: item.title })}
        </p>
        {item.status !== 'available' && (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 p-3 bg-earth-50 dark:bg-earth-800/20 rounded-lg">
            {t('catalog.placeHoldModal.statusNotice', { status: statusLabelI18n(item.status) })}
          </p>
        )}
        <HoldQueueInfo itemId={item.id} status={item.status} />
        {explicitConfirmations && (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg">
            {t('catalog.placeHoldModal.cancelAnytime')}
          </p>
        )}
        {mutationError && (
          <p
            ref={mutationErrorRef}
            id={holdErrorId}
            tabIndex={-1}
            role="alert"
            className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1 mb-3"
          >
            {mutationError}
          </p>
        )}
        <div className="space-y-4 mb-4">
          <div>
            <label htmlFor="hold-format" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              {t('catalog.placeHoldModal.formatLabel')}
            </label>
            <select
              id="hold-format"
              value={selectedItemId}
              onChange={(e) => { setSelectedItemId(Number(e.target.value)); if (mutationError) setMutationError('') }}
              aria-describedby={mutationError ? holdErrorId : undefined}
              className="w-full px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              {formats.length > 0 ? (
                formats.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.label}{f.status === 'available' ? ` — ${statusLabelI18n('available')}` : ''}
                  </option>
                ))
              ) : (
                <option value={item.id}>{formatItemType(item.item_type)}</option>
              )}
            </select>
          </div>
          <div>
            <label htmlFor="pickup-location" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              {t('catalog.placeHoldModal.pickupLocationLabel')}
            </label>
            <select
              id="pickup-location"
              value={selectedBranchId ?? ''}
              onChange={(e) => setSelectedBranchId(e.target.value ? Number(e.target.value) : undefined)}
              aria-describedby={mutationError ? holdErrorId : undefined}
              className="w-full px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              <option value="">{t('catalog.placeHoldModal.defaultBranch')}</option>
              {branches?.map((branch) => (
                <option key={branch.id} value={branch.id}>
                  {branch.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex gap-3 justify-end">
          <Button variant="secondary"
            onClick={onClose}
          >
            {t('common.cancel')}
          </Button>
          <Button variant="primary"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                {t('catalog.placeHoldModal.placingHold')}
              </>
            ) : (
              <>
                <Check aria-hidden="true" className="w-4 h-4" />
                {t('catalog.placeHoldModal.confirmHold')}
              </>
            )}
          </Button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
