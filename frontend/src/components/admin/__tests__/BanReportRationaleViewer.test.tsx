/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BanReportRationaleViewer } from '@/components/admin/BanReportRationaleViewer'

const STRINGS: Record<string, string> = {
  'banReports.noRationale': 'No rationale on file',
  'banReports.anticipated':
    'Defense ready ({{reason}} was anticipated)',
  'banReports.notAnticipated':
    'Re-evaluate -- {{reason}} not in documented categories',
}

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      const raw = STRINGS[key] ?? key
      if (!params) return raw
      return Object.entries(params).reduce(
        (acc, [k, v]) =>
          acc.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v)),
        raw,
      )
    },
  }),
}))

describe('BanReportRationaleViewer', () => {
  it('shows "no rationale on file" when rationalePresent is false', () => {
    render(
      <BanReportRationaleViewer
        rationalePresent={false}
        rationaleAnticipated={false}
        primaryUseCase={null}
        banCategory="lgbtq_content"
      />,
    )
    expect(screen.getByText(/No rationale on file/i)).toBeInTheDocument()
  })

  it('shows "defense ready" with reason when anticipated', () => {
    render(
      <BanReportRationaleViewer
        rationalePresent={true}
        rationaleAnticipated={true}
        primaryUseCase="identity_exploration"
        banCategory="lgbtq_content"
      />,
    )
    const el = screen.getByText(/Defense ready.*lgbtq_content/i)
    expect(el).toBeInTheDocument()
    expect(el).toHaveAttribute('title', 'identity_exploration')
  })

  it('shows "re-evaluate" with reason when not anticipated', () => {
    render(
      <BanReportRationaleViewer
        rationalePresent={true}
        rationaleAnticipated={false}
        primaryUseCase="other"
        banCategory="violence"
      />,
    )
    const el = screen.getByText(/Re-evaluate.*violence/i)
    expect(el).toBeInTheDocument()
    expect(el).toHaveAttribute('title', 'other')
  })

  it('renders empty-string title when primaryUseCase is null and anticipated', () => {
    render(
      <BanReportRationaleViewer
        rationalePresent={true}
        rationaleAnticipated={true}
        primaryUseCase={null}
        banCategory="violence"
      />,
    )
    expect(
      screen.getByText(/Defense ready.*violence/i),
    ).toHaveAttribute('title', '')
  })
})
