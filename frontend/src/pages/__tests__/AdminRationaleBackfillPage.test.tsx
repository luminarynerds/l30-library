/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AdminRationaleBackfillPage from '@/pages/AdminRationaleBackfillPage'

const STRINGS: Record<string, string> = {
  'acquisitionRationale.backfillTitle': 'Items missing acquisition rationale',
  'acquisitionRationale.itemsMissing': '{{count}} items have no rationale',
  'acquisitionRationale.itemLink': 'Item #{{id}}',
  'acquisitionRationale.saving': 'Saving...',
}

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      const raw = STRINGS[key] ?? key
      if (!params) return raw
      return Object.entries(params).reduce(
        (acc, [k, v]) => acc.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v)),
        raw,
      )
    },
  }),
}))

vi.mock('@/api/acquisitionRationale', () => ({
  listMissingRationale: vi.fn().mockResolvedValue([1, 2, 3]),
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('AdminRationaleBackfillPage', () => {
  it('lists items missing rationale', async () => {
    render(
      <MemoryRouter>
        <AdminRationaleBackfillPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(/Item #1/)).toBeInTheDocument()
      expect(screen.getByText(/Item #2/)).toBeInTheDocument()
      expect(screen.getByText(/Item #3/)).toBeInTheDocument()
    })
    expect(screen.getByText(/3 items have no rationale/)).toBeInTheDocument()
  })

  it('renders heading from i18n', async () => {
    render(
      <MemoryRouter>
        <AdminRationaleBackfillPage />
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('heading', { name: /Items missing acquisition rationale/ }),
    ).toBeInTheDocument()
  })

  it('shows error when fetch fails', async () => {
    const mod = await import('@/api/acquisitionRationale')
    ;(mod.listMissingRationale as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error('boom'),
    )
    render(
      <MemoryRouter>
        <AdminRationaleBackfillPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('boom')
    })
  })
})
