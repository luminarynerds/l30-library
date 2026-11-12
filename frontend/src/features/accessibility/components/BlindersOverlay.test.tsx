/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BlindersOverlay } from './BlindersOverlay'

const mockUpdateSetting = vi.fn()

vi.mock('../hooks/useAccessibility', () => ({
  useAccessibility: () => ({
    settings: {
      theme: 'light',
      reduceMotion: false,
      blinders: true,
    },
    updateSetting: mockUpdateSetting,
  }),
}))


// Preload English translations. vitest setup.ts does not preload i18n,
// and t() returns raw dotted-path keys when no language is loaded,
// breaking assertions that match resolved English strings.

describe('BlindersOverlay', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.body.classList.remove('blinders-active')
    document.body.style.removeProperty('--blinders-content-width')
    document.body.style.removeProperty('--blinders-max-width')
  })

  it('applies body blinders class and variables when enabled', () => {
    render(<BlindersOverlay enabled />)

    expect(document.body.classList.contains('blinders-active')).toBe(true)
    expect(document.body.style.getPropertyValue('--blinders-content-width')).toBe('60ch')
    expect(document.body.style.getPropertyValue('--blinders-max-width')).toBe('800px')
  })

  it('allows turning blinders off from indicator', async () => {
    const user = userEvent.setup()
    render(<BlindersOverlay enabled />)

    await user.click(screen.getByRole('button', { name: /turn off blinders mode/i }))

    expect(mockUpdateSetting).toHaveBeenCalledWith('blinders', false)
  })

  it('toggles persisted blinders setting with Ctrl/Cmd+B', async () => {
    render(<BlindersOverlay enabled />)

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'b', ctrlKey: true }))
    expect(mockUpdateSetting).toHaveBeenCalledWith('blinders', false)
  })
})
