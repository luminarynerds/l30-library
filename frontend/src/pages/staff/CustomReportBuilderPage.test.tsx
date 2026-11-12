/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import CustomReportBuilderPage from './CustomReportBuilderPage'
import { generateJsonReport } from '../../api/unified-reports-api'
import { listBranches } from '../../api/branch-api'

vi.mock('../../api/unified-reports-api', () => ({
  generateJsonReport: vi.fn(),
  downloadReport: vi.fn(),
}))

vi.mock('../../api/branch-api', () => ({
  listBranches: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('../../components/shells', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('CustomReportBuilderPage sortable header a11y', () => {
  beforeEach(() => {
    ;(listBranches as ReturnType<typeof vi.fn>).mockResolvedValue([])
    ;(generateJsonReport as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: [
        { title: 'Beta', checkouts: 2 },
        { title: 'Alpha', checkouts: 9 },
      ],
    })
  })

  it('renders column headers as keyboard-focusable buttons with aria-sort that toggles', async () => {
    render(wrap(<CustomReportBuilderPage />))

    // Generate the report so ResultsTable renders.
    fireEvent.click(screen.getByRole('button', { name: /generate report/i }))

    // The columnheader starts unsorted and contains a real (keyboard-focusable) button.
    const header = await screen.findByRole('columnheader', { name: /checkouts/i })
    expect(header).toHaveAttribute('aria-sort', 'none')
    const sortBtn = within(header).getByRole('button')

    // Activating sets ascending, then descending.
    fireEvent.click(sortBtn)
    await waitFor(() => expect(header).toHaveAttribute('aria-sort', 'ascending'))
    fireEvent.click(sortBtn)
    await waitFor(() => expect(header).toHaveAttribute('aria-sort', 'descending'))
  })
})
