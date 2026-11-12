/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '../../utils/test-utils'
import FacilitiesSection from '@/components/tech-support/FacilitiesSection'
import type { TechFacilitySection } from '@/api/tech-support-api'

const sections: TechFacilitySection[] = [
  {
    kind: 'computer_lab',
    facilities: [
      { id: 1, label: 'Computers', value: '12 available' },
      { id: 2, label: 'B&W printing', value: '$0.10/page' },
      { id: 3, label: 'WiFi', value: 'Free throughout building' },
    ],
  },
  {
    kind: 'printer',
    facilities: [
      { id: 10, label: 'Main Floor Computer Lab', value: 'B&W and color' },
      { id: 11, label: 'Second Floor Reference', value: 'B&W only' },
    ],
  },
]

describe('FacilitiesSection', () => {
  it('renders nothing when sections array is empty', () => {
    const { container } = render(<FacilitiesSection sections={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders computer_lab kind with label/value chips', () => {
    render(<FacilitiesSection sections={sections} />)
    expect(screen.getByText(/Public Computer Lab/i)).toBeInTheDocument()
    expect(screen.getByText(/12 available/i)).toBeInTheDocument()
    expect(screen.getByText(/\$0.10\/page/)).toBeInTheDocument()
  })

  it('renders printer kind with label/value cards', () => {
    render(<FacilitiesSection sections={sections} />)
    expect(screen.getByText(/Printer Locations/i)).toBeInTheDocument()
    expect(screen.getByText(/Main Floor Computer Lab/i)).toBeInTheDocument()
    expect(screen.getByText(/Second Floor Reference/i)).toBeInTheDocument()
    expect(screen.getByText(/B&W only/i)).toBeInTheDocument()
  })

  it('keys section blocks on `kind`, not display strings', () => {
    const { container } = render(<FacilitiesSection sections={sections} />)
    expect(container.querySelector('[data-facility-kind="computer_lab"]')).not.toBeNull()
    expect(container.querySelector('[data-facility-kind="printer"]')).not.toBeNull()
  })
})
