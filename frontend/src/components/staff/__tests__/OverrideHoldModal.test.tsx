/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

// FocusTrap (used by ModalBackdrop) requires a real DOM — stub it in jsdom.
vi.mock('focus-trap-react', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// Both '@/i18n' and '@/i18n/I18nContext' need stubs — Button uses the latter.
const tFn = (key: string) => key
vi.mock('@/i18n', () => ({ useTranslation: () => ({ t: tFn }) }))
vi.mock('@/i18n/I18nContext', () => ({ useTranslation: () => ({ t: tFn }) }))

import { OverrideHoldModal } from '../OverrideHoldModal'
import type { HoldOverrideInfo } from '../OverrideHoldModal'

const baseInfo: HoldOverrideInfo = {
  holdId: 7,
  heldPatronName: 'Jordan S.',
  patronOnWay: false,
  queueLength: 2,
}

describe('OverrideHoldModal', () => {
  it('shows the held patron name and walk-in patron name', () => {
    render(
      <OverrideHoldModal
        holdOverride={baseInfo}
        walkInPatronName="Casey Walk-In"
        isSubmitting={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )
    expect(screen.getAllByText(/Jordan S\./).length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText(/Casey Walk-In/)).toBeInTheDocument()
  })

  it('shows the on-the-way warning only when patronOnWay is true', () => {
    const { rerender } = render(
      <OverrideHoldModal
        holdOverride={baseInfo}
        walkInPatronName="Casey Walk-In"
        isSubmitting={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )
    expect(screen.queryByText(/on their way/i)).not.toBeInTheDocument()
    rerender(
      <OverrideHoldModal
        holdOverride={{ ...baseInfo, patronOnWay: true }}
        walkInPatronName="Casey Walk-In"
        isSubmitting={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )
    expect(screen.getByText(/on their way/i)).toBeInTheDocument()
  })

  it('confirms with the selected disposition (defaults to bump_to_front)', () => {
    const onConfirm = vi.fn()
    render(
      <OverrideHoldModal
        holdOverride={baseInfo}
        walkInPatronName="Casey Walk-In"
        isSubmitting={false}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /override checkout/i }))
    expect(onConfirm).toHaveBeenCalledWith('bump_to_front')
  })

  it('confirms with cancel when that option is chosen', () => {
    const onConfirm = vi.fn()
    render(
      <OverrideHoldModal
        holdOverride={baseInfo}
        walkInPatronName="Casey Walk-In"
        isSubmitting={false}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    )
    fireEvent.click(screen.getByLabelText(/cancel it/i))
    fireEvent.click(screen.getByRole('button', { name: /override checkout/i }))
    expect(onConfirm).toHaveBeenCalledWith('cancel')
  })
})
