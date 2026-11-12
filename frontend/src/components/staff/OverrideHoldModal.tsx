/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

export interface HoldOverrideInfo {
  holdId: number | null
  heldPatronName: string
  patronOnWay: boolean
  queueLength: number
}

export type HoldDisposition = 'bump_to_front' | 'cancel'

interface OverrideHoldModalProps {
  holdOverride: HoldOverrideInfo
  walkInPatronName: string
  isSubmitting: boolean
  onConfirm: (disposition: HoldDisposition) => void
  onCancel: () => void
}

export function OverrideHoldModal({
  holdOverride,
  walkInPatronName,
  isSubmitting,
  onConfirm,
  onCancel,
}: OverrideHoldModalProps): React.ReactElement {
  const [disposition, setDisposition] = useState<HoldDisposition>('bump_to_front')

  return (
    <ModalBackdrop
      onClose={onCancel}
      labelledBy="override-hold-title"
      describedBy="override-hold-desc"
      role="alertdialog"
    >
      <div className="w-full max-w-md rounded-xl bg-lsc-white dark:bg-earth-800 p-6 shadow-lg">
        <h2
          id="override-hold-title"
          className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
        >
          This item is on hold for {holdOverride.heldPatronName}
        </h2>

        {holdOverride.patronOnWay && (
          <p className="mt-3 flex items-start gap-2 rounded-lg bg-status-warning-50 dark:bg-status-warning-900/20 p-3 text-sm text-status-warning-800 dark:text-status-warning-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" aria-hidden="true" />
            <span>{holdOverride.heldPatronName} has indicated they are on their way to pick this up.</span>
          </p>
        )}

        <p id="override-hold-desc" className="mt-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
          Check it out to <strong>{walkInPatronName}</strong> anyway?
        </p>

        <fieldset className="mt-4">
          <legend className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
            What happens to {holdOverride.heldPatronName}'s hold?
          </legend>
          <label className="mt-2 flex items-start gap-2 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
            <input
              type="radio"
              name="hold-disposition"
              className="mt-1"
              checked={disposition === 'bump_to_front'}
              onChange={() => setDisposition('bump_to_front')}
            />
            <span>Keep it &mdash; bump to the front of the line</span>
          </label>
          <label className="mt-2 flex items-start gap-2 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
            <input
              type="radio"
              name="hold-disposition"
              className="mt-1"
              checked={disposition === 'cancel'}
              onChange={() => setDisposition('cancel')}
            />
            <span>Cancel it</span>
          </label>
        </fieldset>

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => onConfirm(disposition)}
            disabled={isSubmitting}
          >
            Override checkout
          </Button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
