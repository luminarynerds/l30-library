/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom/vitest" />
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import AutoSaveIndicator from '@/components/AutoSaveIndicator'

describe('AutoSaveIndicator', () => {
  it('shows disabled hint when disabled is true, regardless of lastSaved', () => {
    render(
      <AutoSaveIndicator
        status="idle"
        lastSaved={new Date()}
        disabled={true}
      />
    )
    expect(screen.getByText(/enter a title to save/i)).toBeInTheDocument()
    expect(screen.queryByText(/last saved/i)).not.toBeInTheDocument()
  })

  it('shows last-saved when not disabled', () => {
    render(
      <AutoSaveIndicator
        status="idle"
        lastSaved={new Date()}
        disabled={false}
      />
    )
    expect(screen.getByText(/last saved/i)).toBeInTheDocument()
  })
})
