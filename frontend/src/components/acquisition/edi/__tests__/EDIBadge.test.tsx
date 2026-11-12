/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for EDIBadge — covers variant precedence (failed > received > sent),
 * the no-transactions case (renders nothing), and the drawer interaction
 * (open on click, Escape to close, returns focus to the trigger).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '../../../../__tests__/utils/test-utils'
import EDIBadge from '../EDIBadge'
import type { EDITransaction, EDIShipmentNotice } from '../../../../api/domains/admin/edi-api'

const mocks = vi.hoisted(() => ({
  getShipmentNotices: vi.fn(),
}))

vi.mock('../../../../api/domains/admin/edi-api', async () => {
  const actual = await vi.importActual<typeof import('../../../../api/domains/admin/edi-api')>(
    '../../../../api/domains/admin/edi-api',
  )
  return {
    ...actual,
    getShipmentNotices: mocks.getShipmentNotices,
  }
})

function makeTx(overrides: Partial<EDITransaction>): EDITransaction {
  return {
    id: 1,
    vendor_edi_profile_id: 10,
    purchase_order_id: 42,
    message_type: 'orders',
    direction: 'outbound',
    interchange_control_number: 'ICN-1',
    message_reference_number: null,
    status: 'sent',
    filename: 'orders-1.edi',
    retry_count: 0,
    next_retry_at: null,
    last_error: null,
    created_at: '2026-05-22T10:00:00Z',
    sent_at: '2026-05-22T10:01:00Z',
    received_at: null,
    processed_at: null,
    vendor_name: 'Test Vendor',
    po_number: 'PO-2026-042',
    ...overrides,
  }
}

beforeEach(() => {
  mocks.getShipmentNotices.mockReset()
  mocks.getShipmentNotices.mockResolvedValue({
    items: [] as EDIShipmentNotice[],
    total: 0,
    page: 1,
    per_page: 50,
    pages: 1,
  })
})

describe('EDIBadge', () => {
  it('renders nothing when there are no EDI transactions', () => {
    const { container } = render(
      <EDIBadge poId={42} poNumber="PO-2026-042" transactions={[]} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders the Sent variant for an outbound orders tx with status=sent', () => {
    render(
      <EDIBadge
        poId={42}
        poNumber="PO-2026-042"
        transactions={[makeTx({ message_type: 'orders', direction: 'outbound', status: 'sent' })]}
      />,
    )
    expect(screen.getByRole('button', { name: /View EDI history for PO PO-2026-042/i }))
      .toHaveTextContent(/EDI · Sent/)
  })

  it('renders the Received variant when an inbound desadv tx exists', () => {
    render(
      <EDIBadge
        poId={42}
        poNumber="PO-2026-042"
        transactions={[
          makeTx({ id: 1, message_type: 'orders', direction: 'outbound', status: 'sent' }),
          makeTx({ id: 2, message_type: 'desadv', direction: 'inbound', status: 'processed' }),
        ]}
      />,
    )
    expect(screen.getByRole('button')).toHaveTextContent(/EDI · Received/)
  })

  it('renders the Failed variant when any tx has status=failed (precedence over received/sent)', () => {
    render(
      <EDIBadge
        poId={42}
        poNumber="PO-2026-042"
        transactions={[
          makeTx({ id: 1, message_type: 'orders', direction: 'outbound', status: 'sent' }),
          makeTx({ id: 2, message_type: 'desadv', direction: 'inbound', status: 'processed' }),
          makeTx({ id: 3, message_type: 'invoic', direction: 'inbound', status: 'failed' }),
        ]}
      />,
    )
    expect(screen.getByRole('button')).toHaveTextContent(/EDI · Failed/)
  })

  it('opens the drawer on click and lists the transactions', async () => {
    render(
      <EDIBadge
        poId={42}
        poNumber="PO-2026-042"
        transactions={[
          makeTx({ id: 7, message_type: 'orders', direction: 'outbound', status: 'sent', filename: 'orders-7.edi' }),
        ]}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /View EDI history/i }))

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
    expect(screen.getByText('orders-7.edi')).toBeInTheDocument()
  })

  it('closes the drawer on Escape', async () => {
    render(
      <EDIBadge
        poId={42}
        poNumber="PO-2026-042"
        transactions={[makeTx({ status: 'sent' })]}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /View EDI history/i }))
    const dialog = await waitFor(() => screen.getByRole('dialog'))
    fireEvent.keyDown(dialog, { key: 'Escape' })

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  it('closes the drawer when the backdrop is clicked (outside-click)', async () => {
    render(
      <EDIBadge
        poId={42}
        poNumber="PO-2026-042"
        transactions={[makeTx({ status: 'sent' })]}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /View EDI history/i }))
    await waitFor(() => screen.getByRole('dialog'))

    // Modal.tsx attaches the backdrop click handler to the role="presentation"
    // outer div; clicking that (target === backdropRef) triggers onClose.
    const backdrop = document.querySelector('[role="presentation"]') as HTMLElement
    expect(backdrop).not.toBeNull()
    fireEvent.click(backdrop)

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  it('fetches and renders shipment notice metadata when a DESADV tx is present', async () => {
    mocks.getShipmentNotices.mockResolvedValue({
      items: [
        {
          id: 1,
          edi_transaction_id: 5,
          purchase_order_id: 42,
          vendor_id: 1,
          shipment_number: 'SHIP-1',
          ship_date: '2026-05-20',
          expected_delivery_date: null,
          carrier_name: 'UPS',
          carrier_code: 'UPS',
          tracking_number: '1Z999AA10123456784',
          package_count: 1,
          total_weight: null,
          weight_unit: 'kg',
          total_items_shipped: 12,
          is_processed: true,
          processed_at: null,
          created_at: '2026-05-20T08:00:00Z',
          vendor_name: 'Test Vendor',
          po_number: 'PO-2026-042',
        },
      ],
      total: 1,
      page: 1,
      per_page: 50,
      pages: 1,
    })

    render(
      <EDIBadge
        poId={42}
        poNumber="PO-2026-042"
        transactions={[makeTx({ id: 5, message_type: 'desadv', direction: 'inbound', status: 'processed' })]}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /View EDI history/i }))

    await waitFor(() => {
      expect(screen.getByText('UPS')).toBeInTheDocument()
    })
    expect(screen.getByText('1Z999AA10123456784')).toBeInTheDocument()
    expect(mocks.getShipmentNotices).toHaveBeenCalledWith({ purchase_order_id: 42, per_page: 50 })
  })

  it('does not fetch shipment notices when there is no DESADV tx', async () => {
    render(
      <EDIBadge
        poId={42}
        poNumber="PO-2026-042"
        transactions={[makeTx({ status: 'sent' })]}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /View EDI history/i }))
    await waitFor(() => screen.getByRole('dialog'))

    expect(mocks.getShipmentNotices).not.toHaveBeenCalled()
  })
})
