/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LoginPromptModal from '@/components/LoginPromptModal'

vi.mock('@/i18n', async () => {
  const actual = await vi.importActual<typeof import('@/i18n')>('@/i18n')
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => actual.getTranslation(key, 'en'),
      language: 'en',
      isRTL: false,
    }),
  }
})


function renderModal(onClose = vi.fn()) {
  return {
    onClose,
    ...render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <LoginPromptModal onClose={onClose} />
      </MemoryRouter>
    ),
  }
}

describe('LoginPromptModal', () => {
  it('renders three action buttons (Log in, Create account, Cancel)', () => {
    renderModal()
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
    // Two buttons share the "Cancel" name (X icon button + text button); both should exist
    expect(screen.getAllByRole('button', { name: /cancel/i }).length).toBeGreaterThanOrEqual(1)
  })

  it('calls onClose when the cancel text button is clicked', () => {
    const onClose = vi.fn()
    renderModal(onClose)
    const cancels = screen.getAllByRole('button', { name: /cancel/i })
    const last = cancels[cancels.length - 1]!
    fireEvent.click(last)
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when Escape is pressed', () => {
    const onClose = vi.fn()
    renderModal(onClose)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })
})
