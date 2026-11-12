/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { components } from '@/api/generated/schema'
import VendorComparison from '../VendorComparison'

type Performance = components['schemas']['VendorPerformanceResponse']

const vendors = [
  { id: 2, name: 'Midwest Tape', contact_name: null, email: null, phone: null, is_active: true },
  { id: 5, name: 'Ingram Library Services', contact_name: null, email: null, phone: null, is_active: true },
  { id: 3, name: 'EBSCO Information Services', contact_name: null, email: null, phone: null, is_active: true },
]

const midwest: Performance = {
  vendor_id: 2, vendor_name: 'Midwest Tape', total_orders: 4, total_spent: 829.05,
  average_delivery_days: 13, fill_rate: 0.3571, on_time_rate: 1,
  recent_orders: [
    { po_number: 'PO-2026-002', order_date: '2026-01-15', status: 'received',
      total_amount: 312.85, items_ordered: 5, items_received: 5, delivery_days: 13 },
    { po_number: 'PO-202606-FBD35A', order_date: '2026-06-07', status: 'draft',
      total_amount: 28, items_ordered: 2, items_received: 0, delivery_days: null },
  ],
}
const ingram: Performance = {
  vendor_id: 5, vendor_name: 'Ingram Library Services', total_orders: 7, total_spent: 1758.58,
  average_delivery_days: 6, fill_rate: 0.6047, on_time_rate: 1, recent_orders: [],
}
const noOrders: Performance = {
  vendor_id: 3, vendor_name: 'EBSCO Information Services', total_orders: 0, total_spent: 0,
  average_delivery_days: null, fill_rate: null, on_time_rate: null, recent_orders: [],
}

const formatMoney = (amount: number) => `$${amount.toFixed(2)}`

function serve(responses: Performance[] = [midwest, ingram, noOrders]) {
  vi.mocked(fetch).mockImplementation(async (input) => {
    const url = String(input)
    const response = responses.find((p) => url.endsWith(`/acquisition/vendors/${p.vendor_id}/performance`))
    if (!response) throw new Error(`Unexpected request: ${url}`)
    return new Response(JSON.stringify(response), { status: 200, headers: { 'Content-Type': 'application/json' } })
  })
}

function show() {
  render(<VendorComparison token="test-token" vendors={vendors} formatMoney={formatMoney} />)
}

describe('VendorComparison backend response contract', () => {
  beforeEach(() => { vi.mocked(fetch).mockReset(); serve() })
  afterEach(cleanup)

  it('shows real delivery averages and scales fractional rates on vendor cards', async () => {
    show()
    const card = screen.getByRole('button', { name: /Midwest Tape/ })
    expect(await within(card).findByText('13.0 days')).toBeInTheDocument()
    expect(within(card).getByText('35.7%')).toBeInTheDocument()
    expect(within(card).getByText('On-time: 100%')).toHaveClass('bg-status-success-100')
    expect(within(card).getByText('$829.05')).toBeInTheDocument()
  })

  it('opens backend recent orders with their amounts and delivery values', async () => {
    const user = userEvent.setup()
    show()
    await screen.findAllByText('On-time: 100%')
    await user.click(screen.getByRole('button', { name: /Midwest Tape/ }))
    const table = await screen.findByRole('table')
    const received = within(table).getByRole('row', { name: /PO-2026-002/ })
    expect(within(received).getByText('Jan 15, 2026')).toBeInTheDocument()
    expect(within(received).getByText('$312.85')).toBeInTheDocument()
    expect(within(received).getByText('13 days')).toBeInTheDocument()
    const draft = within(table).getByRole('row', { name: /PO-202606-FBD35A/ })
    expect(within(draft).getByText('$28.00')).toBeInTheDocument()
    expect(within(draft).getByText('—')).toBeInTheDocument()
  })

  it('compares two vendors using the same delivery averages and percentages', async () => {
    const user = userEvent.setup()
    show()
    await screen.findByText('$829.05')
    await user.click(screen.getByRole('button', { name: 'Compare Vendors' }))
    await user.click(screen.getByRole('button', { name: 'Midwest Tape' }))
    await user.click(screen.getByRole('button', { name: 'Ingram Library Services' }))
    const table = await screen.findByRole('table')
    const delivery = within(table).getByRole('row', { name: /Avg Delivery Days/ })
    expect(within(delivery).getByText('13.0 days')).toBeInTheDocument()
    expect(within(delivery).getByText('6.0 days')).toHaveClass('text-status-success-600')
    const fill = within(table).getByRole('row', { name: /Fill Rate/ })
    expect(within(fill).getByText('35.7%')).toBeInTheDocument()
    expect(within(fill).getByText('60.5%')).toBeInTheDocument()
    expect(within(table).getAllByText('100.0%')).toHaveLength(2)
  })

  it('shows absent measurements as unavailable, without a poor-performance rating', async () => {
    show()
    const card = screen.getByRole('button', { name: /EBSCO Information Services/ })
    expect(await within(card).findByText('No delivery data')).toBeInTheDocument()
    expect(within(card).getByText('No fill data')).toBeInTheDocument()
    expect(within(card).getByText('On-time: No delivery data')).not.toHaveClass('bg-status-danger-100')
    expect(within(card).queryByText('0.0 days')).not.toBeInTheDocument()
    expect(within(card).queryByText('0.0%')).not.toBeInTheDocument()
  })

  it('excludes absent measurements from best-vendor comparisons', async () => {
    const user = userEvent.setup()
    show()
    await screen.findByText('$829.05')
    await user.click(screen.getByRole('button', { name: 'Compare Vendors' }))
    await user.click(screen.getByRole('button', { name: 'Midwest Tape' }))
    await user.click(screen.getByRole('button', { name: 'EBSCO Information Services' }))
    const table = await screen.findByRole('table')
    const delivery = within(table).getByRole('row', { name: /Avg Delivery Days/ })
    expect(within(delivery).getByText('13.0 days')).toHaveClass('text-status-success-600')
    expect(within(delivery).getByText('No delivery data')).not.toHaveClass('text-status-success-600')
    const fill = within(table).getByRole('row', { name: /Fill Rate/ })
    expect(within(fill).getByText('No fill data')).not.toHaveClass('text-status-danger-600')
  })

  it('keeps measured zeroes distinct from missing data and reports empty history', async () => {
    const user = userEvent.setup()
    serve([{ ...midwest, average_delivery_days: 0, fill_rate: 0, on_time_rate: 0, recent_orders: [] }, ingram, noOrders])
    show()
    const card = screen.getByRole('button', { name: /Midwest Tape/ })
    expect(await within(card).findByText('0.0 days')).toBeInTheDocument()
    expect(within(card).getByText('0.0%')).toBeInTheDocument()
    expect(within(card).getByText('On-time: 0%')).toHaveClass('bg-status-danger-100')
    await user.click(card)
    expect(screen.getByText('No order history available for Midwest Tape.')).toBeInTheDocument()
  })
})
