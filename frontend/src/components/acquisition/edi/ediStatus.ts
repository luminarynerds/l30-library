/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Helpers for deriving EDI provenance state from a list of transactions
 * belonging to a single PO. Kept separate so it's easy to unit-test.
 */
import type { EDITransaction } from '@/api/domains/admin/edi-api'

export type EDIBadgeVariant = 'failed' | 'received' | 'sent'

export interface EDIBadgeDescriptor {
  variant: EDIBadgeVariant
  /** translation key suffix under acquisitionsEdi.badge.* */
  labelKey: 'failed' | 'received' | 'sent'
  /** safe English fallback for the t() defaultValue */
  fallback: string
}

export function deriveEDIBadge(transactions: EDITransaction[]): EDIBadgeDescriptor | null {
  if (transactions.length === 0) return null

  if (transactions.some((tx) => tx.status === 'failed')) {
    return { variant: 'failed', labelKey: 'failed', fallback: 'EDI · Failed' }
  }

  if (transactions.some((tx) => tx.message_type === 'desadv' && tx.direction === 'inbound')) {
    return { variant: 'received', labelKey: 'received', fallback: 'EDI · Received' }
  }

  if (
    transactions.some(
      (tx) =>
        tx.message_type === 'orders' &&
        tx.direction === 'outbound' &&
        tx.status === 'sent',
    )
  ) {
    return { variant: 'sent', labelKey: 'sent', fallback: 'EDI · Sent' }
  }

  return null
}

export function groupTransactionsByPO(
  transactions: EDITransaction[],
): Map<number, EDITransaction[]> {
  const map = new Map<number, EDITransaction[]>()
  for (const tx of transactions) {
    if (tx.purchase_order_id == null) continue
    const existing = map.get(tx.purchase_order_id)
    if (existing) existing.push(tx)
    else map.set(tx.purchase_order_id, [tx])
  }
  return map
}
