/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useId } from 'react'
import { Modal } from './Modal'
import { Button } from './Button'
import { t } from '@/i18n'

export interface ConfirmDialogProps {
  open: boolean
  title: string
  body: React.ReactNode
  confirmLabel: string
  tone?: 'danger' | 'default'
  onConfirm: () => void
  onCancel: () => void
}

/**
 * Review step for a staff action that would otherwise fire immediately.
 * Built on Modal, so it inherits FocusTrap, Escape-to-cancel, and role=dialog.
 *
 * For a destructive (tone="danger") confirmation, focus goes to the Cancel
 * button instead of Modal's default (the first tabbable node, which is the
 * header's close/X button). Button isn't a forwardRef component, so instead
 * of a ref we give the Cancel button a stable id and pass Modal an
 * `initialFocus` function that resolves it via `getElementById`. Modal
 * forwards that straight into focus-trap's own `initialFocus` option, which
 * focus-trap evaluates itself (including on its internal delayed refocus)
 * rather than racing it against a separately-applied native `autoFocus`.
 */
export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  tone = 'default',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const cancelButtonId = useId()

  if (!open) return null

  return (
    <Modal
      isOpen={open}
      onClose={onCancel}
      title={title}
      size="md"
      initialFocus={
        tone === 'danger'
          ? () => document.getElementById(cancelButtonId)
          : undefined
      }
      footer={
        <div className="flex justify-end gap-2 w-full">
          <Button
            id={cancelButtonId}
            type="button"
            variant="secondary"
            onClick={onCancel}
          >
            {t('common.cancel', 'Cancel')}
          </Button>
          <Button
            type="button"
            variant={tone === 'danger' ? 'danger' : 'primary'}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      }
    >
      <div className="text-sm">{body}</div>
    </Modal>
  )
}

export default ConfirmDialog
