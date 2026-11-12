/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChallengeRationaleViewer } from '@/components/challenges/ChallengeRationaleViewer'

const STRINGS: Record<string, string> = {
  'acquisitionRationale.title': 'Why we acquired this',
  'acquisitionRationale.signalLabel': 'What prompted this acquisition?',
  'acquisitionRationale.policyClauseLabel': 'Policy clause (optional)',
  'acquisitionRationale.primaryUseCaseLabel': 'Primary use case',
  'acquisitionRationale.weedingConditionLabel': 'When would we weed this?',
  'acquisitionRationale.challengeAnticipationLabel':
    'Anticipated this challenge category?',
  'acquisitionRationale.anticipatedYes':
    'Yes -- {{reason}} was anticipated and documented at acquisition.',
  'acquisitionRationale.notAnticipated':
    'Not anticipated -- {{reason}} was not in the documented challenge categories.',
  'acquisitionRationale.noRationaleOnFile':
    'No acquisition rationale on file for this item.',
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

const baseRationale = {
  id: 1,
  catalog_item_id: 5,
  created_by_id: null,
  created_at: '',
  updated_at: '',
  signal_type: 'gap_in_collection',
  signal_ref_table: null,
  signal_ref_id: null,
  signal_note: 'gap in YA representation',
  policy_clause: 'CDP-3.2',
  primary_use_case_slug: 'identity_exploration',
  secondary_use_case_slugs: [],
  weeding_condition: 'signal_persistence',
  weeding_signal_note: null,
  anticipated_challenge_reasons: ['lgbtq_content'] as const,
  anticipated_challenge_acknowledged: true,
  patron_visible: false,
  public_summary: null,
}

describe('ChallengeRationaleViewer', () => {
  it('shows rationale fields when present', () => {
    render(
      <ChallengeRationaleViewer
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        rationale={baseRationale as any}
        challengeReason="lgbtq_content"
      />,
    )
    expect(screen.getByText(/gap in YA representation/)).toBeInTheDocument()
    expect(screen.getByText(/CDP-3.2/)).toBeInTheDocument()
    expect(
      screen.getByText(/anticipated and documented/i),
    ).toBeInTheDocument()
  })

  it('flags unanticipated challenge category', () => {
    render(
      <ChallengeRationaleViewer

        rationale={
          {
            ...baseRationale,
            anticipated_challenge_reasons: ['violence'],
          } as any
        }
        challengeReason="lgbtq_content"
      />,
    )
    expect(
      screen.getByText(/not in the documented challenge categories/i),
    ).toBeInTheDocument()
  })

  it('handles missing rationale gracefully', () => {
    render(
      <ChallengeRationaleViewer rationale={null} challengeReason="other" />,
    )
    expect(
      screen.getByText(/No acquisition rationale on file/i),
    ).toBeInTheDocument()
  })

  it('omits policy clause section when null', () => {
    render(
      <ChallengeRationaleViewer
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        rationale={{ ...baseRationale, policy_clause: null } as any}
        challengeReason="lgbtq_content"
      />,
    )
    expect(screen.queryByText(/Policy clause/i)).not.toBeInTheDocument()
  })
})
