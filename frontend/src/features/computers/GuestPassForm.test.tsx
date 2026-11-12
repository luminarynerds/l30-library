/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { GuestPassForm } from './GuestPassForm'

describe('GuestPassForm', () => {
  it('submitting with empty name renders inline error (no alert dialog)', () => {
    const onSubmit = vi.fn()
    // Note: setting `required` would also block submission via the browser;
    // we trigger via the form's submit event to bypass that and confirm
    // the JS-layer error handling still runs.
    const { container } = render(<GuestPassForm onSubmit={onSubmit} />)
    const form = container.querySelector('form') as HTMLFormElement
    expect(form).not.toBeNull()
    fireEvent.submit(form)

    expect(onSubmit).not.toHaveBeenCalled()
    const alerts = screen.getAllByRole('alert')
    expect(alerts.length).toBeGreaterThan(0)
  })

  it('submitting with valid data calls onSubmit with cleaned payload (no empty fields, no empty allowed types)', () => {
    const onSubmit = vi.fn()
    render(<GuestPassForm onSubmit={onSubmit} />)
    const nameInput = screen.getByLabelText(/guest name/i) as HTMLInputElement
    fireEvent.change(nameInput, { target: { value: 'Jane Doe' } })

    const form = nameInput.closest('form') as HTMLFormElement
    fireEvent.submit(form)

    expect(onSubmit).toHaveBeenCalledTimes(1)
    const payload = onSubmit.mock.calls[0]![0]
    expect(payload.guest_name).toBe('Jane Doe')
    expect(payload.max_sessions).toBe(1)
    expect(payload.max_duration_minutes_per_session).toBe(60)
    // allowed_computer_types is stripped when empty via clean()
    expect(payload.allowed_computer_types).toBeUndefined()
  })

  it('toggling a computer-type checkbox includes that type in submitted payload', () => {
    const onSubmit = vi.fn()
    render(<GuestPassForm onSubmit={onSubmit} />)
    const nameInput = screen.getByLabelText(/guest name/i) as HTMLInputElement
    fireEvent.change(nameInput, { target: { value: 'Jane' } })

    const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[]
    expect(checkboxes.length).toBeGreaterThan(0)
    fireEvent.click(checkboxes[0]!)

    const form = nameInput.closest('form') as HTMLFormElement
    fireEvent.submit(form)

    expect(onSubmit).toHaveBeenCalled()
    const payload = onSubmit.mock.calls[0]![0]
    expect(Array.isArray(payload.allowed_computer_types)).toBe(true)
    expect(payload.allowed_computer_types).toHaveLength(1)
  })

  it('isLoading={true} disables submit button', () => {
    render(<GuestPassForm onSubmit={vi.fn()} isLoading />)
    const submit = screen.getByRole('button')
    expect(submit).toBeDisabled()
  })
})
