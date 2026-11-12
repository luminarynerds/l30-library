/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { FormInput } from '../FormInput'

describe('FormInput aria-describedby', () => {
  it('references only errorId when error present and no helperText', () => {
    render(
      <FormInput id="email" label="Email" error="Invalid email" />
    )
    const input = screen.getByRole('textbox', { name: 'Email' })
    expect(input).toHaveAttribute('aria-describedby', 'email-error')
  })

  it('references only helperId when helperText present and no error', () => {
    render(
      <FormInput id="email" label="Email" helperText="We never share your email" />
    )
    const input = screen.getByRole('textbox', { name: 'Email' })
    expect(input).toHaveAttribute('aria-describedby', 'email-helper')
    expect(screen.getByText('We never share your email')).toBeInTheDocument()
  })

  it('references BOTH errorId and helperId when both error and helperText are present', () => {
    render(
      <FormInput
        id="email"
        label="Email"
        error="Invalid email"
        helperText="We never share your email"
      />
    )
    const input = screen.getByRole('textbox', { name: 'Email' })
    const describedBy = input.getAttribute('aria-describedby') ?? ''
    expect(describedBy).toContain('email-error')
    expect(describedBy).toContain('email-helper')
  })

  it('renders helperText element even when error is present', () => {
    render(
      <FormInput
        id="email"
        label="Email"
        error="Invalid email"
        helperText="We never share your email"
      />
    )
    expect(screen.getByText('We never share your email')).toBeInTheDocument()
    expect(document.getElementById('email-helper')).not.toBeNull()
  })

  it('has no aria-describedby when neither error nor helperText', () => {
    render(<FormInput id="email" label="Email" />)
    const input = screen.getByRole('textbox', { name: 'Email' })
    expect(input).not.toHaveAttribute('aria-describedby')
  })
})
