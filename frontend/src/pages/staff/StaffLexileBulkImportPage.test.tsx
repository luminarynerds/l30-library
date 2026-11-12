/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import StaffLexileBulkImportPage from './StaffLexileBulkImportPage'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (k: string, p?: Record<string, unknown>) =>
      p ? `${k}::${JSON.stringify(p)}` : k,
  }),
}))

vi.mock('@/utils/tokenStore', () => ({
  getAccessToken: () => 'test-token',
}))

describe('StaffLexileBulkImportPage', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        matched: 2,
        updated: 2,
        skipped_invalid: 0,
        skipped_no_match: 0,
        invalid_rows: [],
        no_match_rows: [],
      }),
    }) as unknown as typeof fetch
  })

  it('uploads CSV and shows result key', async () => {
    render(<StaffLexileBulkImportPage />)
    const file = new File(['isbn,lexile\n9780000000001,750L'], 'lex.csv', { type: 'text/csv' })
    fireEvent.change(screen.getByLabelText('staff_lexile_bulk_upload'), { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: 'staff_lexile_bulk_submit' }))
    await waitFor(() =>
      expect(screen.getByText(/staff_lexile_bulk_result/)).toBeInTheDocument()
    )
  })

  it('shows error key when request fails', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500 }) as unknown as typeof fetch
    render(<StaffLexileBulkImportPage />)
    const file = new File(['isbn,lexile\n9780000000001,750L'], 'lex.csv', { type: 'text/csv' })
    fireEvent.change(screen.getByLabelText('staff_lexile_bulk_upload'), { target: { files: [file] } })
    fireEvent.click(screen.getByRole('button', { name: 'staff_lexile_bulk_submit' }))
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })
})
