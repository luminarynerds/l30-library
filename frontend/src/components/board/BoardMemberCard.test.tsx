/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
// Explicit: the pre-commit hook typechecks staged files with tsc-files, which
// does not load vitest's setupFiles, so the jest-dom matcher types are
// otherwise invisible there and toBeInTheDocument fails to resolve.
import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import BoardMemberCard from './BoardMemberCard'

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

// The off-by-one-month bug below only manifests when the runtime is west of
// UTC, and the runtime zone cannot be changed from inside the test: V8 caches
// it at process start, so assigning process.env.TZ in a beforeAll is a no-op.
// Measured on a UTC host: after setting process.env.TZ = 'America/New_York',
// Intl.DateTimeFormat().resolvedOptions().timeZone still reported 'UTC' and
// getTimezoneOffset() still returned 0. This test previously carried that
// assignment and so asserted a shift that physically could not happen there,
// failing every run on any UTC or east-of-UTC machine (including CI).
//
// getTimezoneOffset() is positive for zones behind UTC. Gate on the real
// runtime instead of pretending to control it. To exercise this case
// deliberately, run vitest with TZ set in the environment before the process
// starts: TZ=America/New_York npx vitest run src/components/board
const isWestOfUtc = new Date('2026-02-01').getTimezoneOffset() > 0

describe('BoardMemberCard', () => {
  it.skipIf(!isWestOfUtc)('documents the off-by-one-month bug: a bare YYYY-MM-DD date at a month boundary renders the wrong month in a west-of-UTC zone', () => {
    // "2026-02-01" parses as 2026-01-31T19:00 in America/New_York, so the
    // year/month-only formatter below currently prints "Jan 2026" instead
    // of the stored "Feb 2026". This is a regression lock on the known bug,
    // not a fix — see BoardMemberCard.tsx:47-52's formatDate.
    renderWithRouter(
      <BoardMemberCard
        id={1}
        full_name="Pat Rivera"
        position="president"
        term_start_date="2026-02-01"
      />
    )

    expect(screen.getByText('Since Jan 2026')).toBeInTheDocument()
    expect(screen.queryByText('Since Feb 2026')).not.toBeInTheDocument()
  })

  it('renders both term_start_date and term_end_date when a full term range is given', () => {
    renderWithRouter(
      <BoardMemberCard
        id={2}
        full_name="Jordan Lee"
        position="treasurer"
        term_start_date="2024-01-15"
        term_end_date="2027-01-15"
      />
    )

    expect(screen.getByText('Jordan Lee')).toBeInTheDocument()
    expect(screen.getByText('Treasurer')).toBeInTheDocument()
    // Both dates render into the same term-range paragraph.
    const termText = screen.getByText(/2024 - .*2027/)
    expect(termText).toBeInTheDocument()
  })
})
