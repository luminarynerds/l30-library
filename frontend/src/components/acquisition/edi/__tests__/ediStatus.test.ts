/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { deriveEDIBadge, groupTransactionsByPO } from '../ediStatus'
import type { EDITransaction } from '../../../../api/domains/admin/edi-api'

function makeTx(overrides: Partial<EDITransaction>): EDITransaction {
  return {
    id: 1,
    vendor_edi_profile_id: 10,
    purchase_order_id: 42,
    message_type: 'orders',
    direction: 'outbound',
    interchange_control_number: null,
    message_reference_number: null,
    status: 'sent',
    filename: null,
    retry_count: 0,
    next_retry_at: null,
    last_error: null,
    created_at: '2026-05-22T10:00:00Z',
    sent_at: null,
    received_at: null,
    processed_at: null,
    vendor_name: null,
    po_number: null,
    ...overrides,
  }
}

describe('deriveEDIBadge', () => {
  it('returns null for an empty transaction list', () => {
    expect(deriveEDIBadge([])).toBeNull()
  })

  it('returns null when no tx matches any spec rule', () => {
    // outbound orders but pending (not sent), no desadv, no failure
    expect(deriveEDIBadge([makeTx({ status: 'pending' })])).toBeNull()
  })

  it('returns sent for an outbound orders tx with status=sent', () => {
    const d = deriveEDIBadge([makeTx({ status: 'sent' })])
    expect(d?.variant).toBe('sent')
    expect(d?.labelKey).toBe('sent')
  })

  it('returns received for an inbound desadv tx', () => {
    const d = deriveEDIBadge([
      makeTx({ message_type: 'desadv', direction: 'inbound', status: 'processed' }),
    ])
    expect(d?.variant).toBe('received')
  })

  it('returns failed when any tx is failed (precedence over sent/received)', () => {
    const d = deriveEDIBadge([
      makeTx({ id: 1, status: 'sent' }),
      makeTx({ id: 2, message_type: 'desadv', direction: 'inbound', status: 'processed' }),
      makeTx({ id: 3, status: 'failed' }),
    ])
    expect(d?.variant).toBe('failed')
  })

  it('returns received when both desadv and sent orders exist (received > sent)', () => {
    const d = deriveEDIBadge([
      makeTx({ id: 1, status: 'sent' }),
      makeTx({ id: 2, message_type: 'desadv', direction: 'inbound', status: 'processed' }),
    ])
    expect(d?.variant).toBe('received')
  })
})

describe('groupTransactionsByPO', () => {
  it('groups by purchase_order_id and skips null PO ids', () => {
    const txs: EDITransaction[] = [
      makeTx({ id: 1, purchase_order_id: 1 }),
      makeTx({ id: 2, purchase_order_id: 1 }),
      makeTx({ id: 3, purchase_order_id: 2 }),
      makeTx({ id: 4, purchase_order_id: null }),
    ]
    const grouped = groupTransactionsByPO(txs)
    expect(grouped.get(1)?.length).toBe(2)
    expect(grouped.get(2)?.length).toBe(1)
    expect(grouped.has(0)).toBe(false)
    expect(grouped.size).toBe(2)
  })
})
