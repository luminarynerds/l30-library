/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe } from 'jest-axe'
import { MemoryRouter } from 'react-router-dom'
import FeatureDisabledNotice, { humanizeFeature } from './FeatureDisabledNotice'

describe('humanizeFeature', () => {
  it('strips _enabled and spaces words', () => {
    expect(humanizeFeature('learning_platform_enabled')).toBe('Learning platform')
    expect(humanizeFeature('board_features_enabled')).toBe('Board features')
  })

  it('keeps known acronyms uppercase', () => {
    expect(humanizeFeature('ai_tools_enabled')).toBe('AI tools')
    expect(humanizeFeature('edi_enabled')).toBe('EDI')
  })
})

describe('FeatureDisabledNotice', () => {
  it('names the feature and offers a way to turn it back on', () => {
    render(
      <MemoryRouter>
        <FeatureDisabledNotice feature="ai_tools_enabled" />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('heading', { name: 'AI tools is turned off' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /manage features/i })).toHaveAttribute(
      'href',
      '/staff/admin/library-config#features',
    )
    expect(screen.getByRole('link', { name: /back to admin/i })).toHaveAttribute(
      'href',
      '/staff/admin',
    )
  })

  it('has no axe violations', async () => {
    const { container } = render(
      <MemoryRouter>
        <FeatureDisabledNotice feature="ai_tools_enabled" />
      </MemoryRouter>,
    )
    expect(await axe(container)).toHaveNoViolations()
  })

  it('tabs through both actions in order with no trap', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <FeatureDisabledNotice feature="ai_tools_enabled" />
      </MemoryRouter>,
    )
    await user.tab()
    expect(screen.getByRole('link', { name: /manage features/i })).toHaveFocus()
    await user.tab()
    expect(screen.getByRole('link', { name: /back to admin/i })).toHaveFocus()
  })
})
