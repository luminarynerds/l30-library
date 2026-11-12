/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Clickable EDI provenance badge for a single PO row. Wraps the shared
 * StatusBadge in a <button>; clicking opens a Modal-backed drawer that
 * lists every EDI transaction (and shipment notice metadata) for the PO.
 *
 * Returns null when there are no EDI transactions for the PO.
 */
import { useState, useId } from 'react'
import { useTranslation } from '@/i18n'
import { StatusBadge, type StatusVariant } from '@/components/ui/StatusBadge'
import { Modal } from '@/components/ui/Modal'
import EDIHistoryDrawer from './EDIHistoryDrawer'
import { deriveEDIBadge } from './ediStatus'
import type { EDITransaction } from '@/api/domains/admin/edi-api'

interface EDIBadgeProps {
  poId: number
  poNumber: string
  transactions: EDITransaction[]
}

const VARIANT_TO_STATUS: Record<'failed' | 'received' | 'sent', StatusVariant> = {
  failed: 'danger',
  received: 'success',
  sent: 'info',
}

export default function EDIBadge({ poId, poNumber, transactions }: EDIBadgeProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const titleId = useId()

  const descriptor = deriveEDIBadge(transactions)
  if (!descriptor) return null

  const label = t(`acquisitionsEdi.badge.${descriptor.labelKey}`, descriptor.fallback)
  const variant = VARIANT_TO_STATUS[descriptor.variant]

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t('acquisitionsEdi.badgeAriaLabel', {
          poNumber,
          defaultValue: `View EDI history for PO ${poNumber}`,
        })}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="inline-flex items-center rounded-full focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1 hover:opacity-80 transition-opacity"
      >
        <StatusBadge variant={variant}>{label}</StatusBadge>
      </button>

      {open && (
        <Modal
          isOpen={open}
          onClose={() => setOpen(false)}
          title={t('acquisitionsEdi.drawerTitle', {
            poNumber,
            defaultValue: `EDI history for PO ${poNumber}`,
          })}
          size="2xl"
        >
          <EDIHistoryDrawer
            poId={poId}
            initialTransactions={transactions}
            titleId={titleId}
          />
        </Modal>
      )}
    </>
  )
}
