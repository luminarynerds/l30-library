/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render } from '@testing-library/react'
import { describe, it, vi } from 'vitest'
import React from 'react'
import { testAccessibility } from '../../../__tests__/utils/accessibility'

// FocusTrap (used by ModalBackdrop) requires a real DOM — stub it, matching
// the pattern used by OverrideHoldModal.test.tsx in this same directory.
vi.mock('focus-trap-react', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// Both '@/i18n' and '@/i18n/I18nContext' need stubs.
vi.mock('@/i18n', () => ({ useTranslation: () => ({ t: (key: string, fallback?: string) => fallback ?? key }), t: (key: string, fallback?: string) => fallback ?? key }))
vi.mock('@/i18n/I18nContext', () => ({ useTranslation: () => ({ t: (key: string, fallback?: string) => fallback ?? key }) }))

import { EquipmentFormModal } from '../EquipmentFormModal'

const baseFormData = {
  name: '',
  equipment_type: 'laptop' as const,
  description: '',
  barcode: '',
  serial_number: '',
  manufacturer: '',
  model: '',
  condition: 'excellent' as const,
  location: '',
  loan_period_days: 14,
  max_renewals: 0,
  deposit_required: '',
  included_accessories: '',
  return_instructions: '',
  notes: '',
}

describe('staff form labels', () => {
  it('EquipmentFormModal has no axe violations', async () => {
    const { container } = render(
      <EquipmentFormModal
        editingEquipment={null}
        formData={baseFormData}
        onChange={() => {}}
        onSubmit={(e) => e.preventDefault()}
        onClose={() => {}}
        isPending={false}
      />,
    )
    await testAccessibility(container)
  })
})
