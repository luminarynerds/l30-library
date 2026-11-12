/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { render, screen, within } from '../../utils/test-utils'
import TriageTiles from '@/components/tech-support/TriageTiles'

describe('TriageTiles', () => {
  it('renders 4 tiles with the expected guide ids', () => {
    render(<TriageTiles />)
    const root = screen.getByTestId('tech-triage-tiles')
    const links = within(root).getAllByRole('link')
    expect(links).toHaveLength(4)

    const ids = links.map((a) => a.getAttribute('data-guide-id'))
    expect(ids).toEqual([
      'password-reset',
      'library-card',
      'check-print-jobs',
      'wifi-troubleshooting',
    ])
  })

  it('exposes hrefs that match the guides registry', () => {
    render(<TriageTiles />)
    const root = screen.getByTestId('tech-triage-tiles')
    const links = within(root).getAllByRole('link')
    const hrefs = links.map((a) => a.getAttribute('href'))
    expect(hrefs).toEqual([
      '/guides/password-reset',
      '/guides/library-card',
      '/guides/check-print-jobs',
      '/guides/wifi-troubleshooting',
    ])
  })

  it('uses plain-language labels (no jargon)', () => {
    render(<TriageTiles />)
    expect(screen.getByText(/Reset my password/i)).toBeInTheDocument()
    expect(screen.getByText(/Can't log in/i)).toBeInTheDocument()
    expect(screen.getByText(/Printing isn't working/i)).toBeInTheDocument()
    expect(screen.getByText(/WiFi won't connect/i)).toBeInTheDocument()
  })
})
