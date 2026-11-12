/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/components/ui/ModalBackdrop', () => ({
  ModalBackdrop: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

// Mock the api -- this is the assertion target.
const mockCheckout = vi.fn()
vi.mock('@/api/parent-onboarding-api', () => ({
  checkoutChildcareRegistration: (...args: unknown[]) => mockCheckout(...args),
}))

import StaffChildcareCheckoutModal from './StaffChildcareCheckoutModal'
import type { ChildcareRegistration } from '@/api/parent-onboarding-api'

const baseReg: ChildcareRegistration = {
  id: 42,
  session_id: 7,
  patron_id: 1,
  child_name: 'Mae',
  child_age_months: 48,
  status: 'checked_in',
  emergency_contact_name: 'E',
  emergency_contact_phone: '5550001111',
  created_at: '2026-06-01T10:00:00Z',
  authorized_pickup: [
    { name: 'Aunt Jo', phone: '5552223333', relationship: 'aunt', id_required: true },
    { name: 'Grandma Lin', phone: '5554445555', relationship: 'grandparent', id_required: false },
  ],
}

function renderModal(reg: ChildcareRegistration) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <StaffChildcareCheckoutModal
        registration={reg}
        open
        onClose={() => {}}
      />
    </QueryClientProvider>,
  )
}

describe('StaffChildcareCheckoutModal', () => {
  beforeEach(() => {
    mockCheckout.mockReset()
    mockCheckout.mockResolvedValue({ ...baseReg, status: 'checked_out' })
  })

  it('submits the selected authorized adult to the checkout API', async () => {
    renderModal(baseReg)

    // Aunt Jo is the first entry; default selection. Switch to Grandma Lin
    // to prove the selection actually drives the payload.
    const grandmaRadio = screen.getByLabelText(/Grandma Lin/i)
    fireEvent.click(grandmaRadio)

    const checkoutBtn = screen.getByRole('button', { name: /Check out$/i })
    fireEvent.click(checkoutBtn)

    await waitFor(() => expect(mockCheckout).toHaveBeenCalledTimes(1))
    expect(mockCheckout).toHaveBeenCalledWith(42, {
      picked_up_by_name: 'Grandma Lin',
      picked_up_by_phone: '5554445555',
      staff_override_reason: undefined,
    })
  })

  it('requires an override reason when registration has no authorized list', async () => {
    renderModal({ ...baseReg, authorized_pickup: [] })

    const checkoutBtn = screen.getByRole('button', { name: /Check out$/i })
    expect(checkoutBtn).toBeDisabled()

    // Fill required override fields
    fireEvent.change(screen.getByLabelText(/Pickup name/i), {
      target: { value: 'Walk-in Adult' },
    })
    fireEvent.change(screen.getByLabelText(/Pickup phone/i), {
      target: { value: '5559998888' },
    })
    fireEvent.change(screen.getByLabelText(/Override reason/i), {
      target: { value: 'Verified verbally with parent on phone' },
    })

    expect(checkoutBtn).not.toBeDisabled()
    fireEvent.click(checkoutBtn)

    await waitFor(() => expect(mockCheckout).toHaveBeenCalledTimes(1))
    expect(mockCheckout).toHaveBeenCalledWith(42, {
      picked_up_by_name: 'Walk-in Adult',
      picked_up_by_phone: '5559998888',
      staff_override_reason: 'Verified verbally with parent on phone',
    })
  })
})
