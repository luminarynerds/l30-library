/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ComputerReservationCard } from './ComputerReservationCard'
import type { Computer } from '@/types/computer'

const baseComputer: Computer = {
  id: 1,
  name: 'PC-01',
  computer_number: 'PC-001',
  computer_type: 'adult',
  has_internet: true,
  has_screen_reader: false,
  has_magnifier: false,
  has_keyboard_options: false,
  has_print_release: true,
  max_session_minutes: 60,
  is_extendable: true,
  max_extension_minutes: 30,
  status: 'available',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  location: 'Main Floor',
  installed_software: ['LibreOffice', 'Firefox'],
}

describe('ComputerReservationCard', () => {
  it('renders computer name and number', () => {
    render(
      <ComputerReservationCard
        computer={baseComputer}
        onReserve={vi.fn()}
        onStartSession={vi.fn()}
        isAvailable
      />
    )
    expect(screen.getByText('PC-01')).toBeInTheDocument()
    expect(screen.getByText('PC-001')).toBeInTheDocument()
  })

  it('renders Accessible badge when any accessibility feature is set', () => {
    render(
      <ComputerReservationCard
        computer={{ ...baseComputer, has_screen_reader: true }}
        onReserve={vi.fn()}
        onStartSession={vi.fn()}
        isAvailable
      />
    )
    // Accessibility chip text comes from the t() namespace; assert presence by role/text fragment
    const chips = screen.getAllByText(/accessible/i)
    expect(chips.length).toBeGreaterThan(0)
  })

  it('reserve button is enabled by default when isAvailable=true (selectedTime initialized to now)', () => {
    render(
      <ComputerReservationCard
        computer={baseComputer}
        onReserve={vi.fn()}
        onStartSession={vi.fn()}
        isAvailable
      />
    )
    const button = screen.getByRole('button', { name: /reserve computer/i })
    expect(button).not.toBeDisabled()
  })

  it('reserve button is hidden when isAvailable=false (controls panel not rendered)', () => {
    render(
      <ComputerReservationCard
        computer={baseComputer}
        onReserve={vi.fn()}
        onStartSession={vi.fn()}
        isAvailable={false}
      />
    )
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('changing duration select updates the value submitted to onReserve', () => {
    const onReserve = vi.fn()
    render(
      <ComputerReservationCard
        computer={baseComputer}
        onReserve={onReserve}
        onStartSession={vi.fn()}
        isAvailable
      />
    )
    const select = screen.getByRole('combobox') as HTMLSelectElement
    fireEvent.change(select, { target: { value: '30' } })
    fireEvent.click(screen.getByRole('button', { name: /reserve computer/i }))
    expect(onReserve).toHaveBeenCalledTimes(1)
    expect(onReserve.mock.calls[0]![0]).toBe(1)
    expect(onReserve.mock.calls[0]![1]).toBeInstanceOf(Date)
    expect(onReserve.mock.calls[0]![2]).toBe(30)
  })

  it('clicking Reserve with default values calls onReserve with (computer.id, Date, 60)', () => {
    const onReserve = vi.fn()
    render(
      <ComputerReservationCard
        computer={baseComputer}
        onReserve={onReserve}
        onStartSession={vi.fn()}
        isAvailable
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /reserve computer/i }))
    expect(onReserve).toHaveBeenCalledTimes(1)
    const [computerId, startTime, duration] = onReserve.mock.calls[0]!
    expect(computerId).toBe(1)
    expect(startTime).toBeInstanceOf(Date)
    expect(duration).toBe(60)
  })

  it('start time input has a min attribute', () => {
    render(
      <ComputerReservationCard
        computer={baseComputer}
        onReserve={vi.fn()}
        onStartSession={vi.fn()}
        isAvailable
      />
    )
    const input = document.querySelector('input[type="datetime-local"]') as HTMLInputElement
    expect(input).not.toBeNull()
    expect(input.getAttribute('min')).toBeTruthy()
    expect(input.getAttribute('min')).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/)
  })
})
