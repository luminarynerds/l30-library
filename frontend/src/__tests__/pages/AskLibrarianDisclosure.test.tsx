/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AiDisclosure } from '../../pages/AskLibrarianPage'

describe('AiDisclosure', () => {
  it('never claims AI before a reply has arrived', () => {
    render(<AiDisclosure mode={null} />)
    expect(screen.getByText(/automated assistant/i)).toBeInTheDocument()
    expect(screen.queryByText(/AI-generated/i)).not.toBeInTheDocument()
  })

  it('says answers come from a written list when the model is off', () => {
    render(<AiDisclosure mode="rule_based" />)
    expect(screen.getByText(/written list of common library questions/i)).toBeInTheDocument()
    expect(screen.queryByText(/AI-generated/i)).not.toBeInTheDocument()
  })

  it('discloses AI generation only when the model actually answered', () => {
    render(<AiDisclosure mode="llm" />)
    expect(screen.getByText(/AI-generated/i)).toBeInTheDocument()
  })

  it('always tells the reader staff can answer instead', () => {
    for (const mode of [null, 'rule_based', 'llm'] as const) {
      const { unmount } = render(<AiDisclosure mode={mode} />)
      expect(screen.getByText(/visit the desk/i)).toBeInTheDocument()
      unmount()
    }
  })
})
