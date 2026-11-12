/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { AcquisitionRationaleForm } from '@/components/cataloging/AcquisitionRationaleForm'

const STRINGS: Record<string, string> = {
  'acquisitionRationale.title': 'Why we acquired this',
  'acquisitionRationale.signalLabel': 'What prompted this acquisition?',
  'acquisitionRationale.signalNote': 'Note about the signal (optional, privacy-safe)',
  'acquisitionRationale.policyClauseLabel': 'Policy clause (optional)',
  'acquisitionRationale.primaryUseCaseLabel': 'Primary use case',
  'acquisitionRationale.secondaryUseCaseLabel': 'Secondary use cases (optional)',
  'acquisitionRationale.weedingConditionLabel': 'When would we weed this?',
  'acquisitionRationale.weedingNoteLabel': 'Weeding signal note (optional)',
  'acquisitionRationale.anticipatedChallengesLabel': 'Anticipated challenge categories',
  'acquisitionRationale.anticipatedAcknowledgeLabel':
    'We anticipated this could be challenged and acquired it anyway',
  'acquisitionRationale.patronVisibleLabel':
    'Show this rationale to patrons (curated public summary required)',
  'acquisitionRationale.publicSummaryLabel': 'Public summary (patron-facing)',
  'acquisitionRationale.save': 'Save rationale',
  'acquisitionRationale.saving': 'Saving...',
  'acquisitionRationale.saved': 'Saved',
  'acquisitionRationale.linkSignalButton': 'Link a signal record',
  'acquisitionRationale.signalCandidatesHeader': 'Possible matching signals',
  'acquisitionRationale.noCandidates': 'No matching signal records found',
  'acquisitionRationale.clearSignal': 'Clear signal link',
  'acquisitionRationale.selectOption': '--',
  'acquisitionRationale.errorPrefix': 'Error: {{message}}',
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
  listBehaviorTags: vi.fn().mockResolvedValue([
    { slug: 'new_parent', label: 'New parent', category: 'life_stage', sort_order: 10, description: null },
    { slug: 'grief_loss', label: 'Grief and loss', category: 'life_stage', sort_order: 20, description: null },
    { slug: 'fix_or_make_something', label: 'Fix or make something', category: 'use_moment', sort_order: 10, description: null },
  ]),
  listSignalCandidates: vi.fn().mockResolvedValue([]),
  getRationale: vi.fn().mockResolvedValue(null),
  createRationale: vi.fn().mockResolvedValue({ id: 1 }),
  updateRationale: vi.fn().mockResolvedValue({ id: 1 }),
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('AcquisitionRationaleForm', () => {
  it('renders required fields after tags load', async () => {
    render(<AcquisitionRationaleForm catalogItemId={5} onSaved={() => {}} />)
    expect(
      await screen.findByLabelText(/What prompted this acquisition\?/i),
    ).toBeInTheDocument()
    expect(screen.getByLabelText(/Primary use case/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/When would we weed this\?/i)).toBeInTheDocument()
  })

  it('disables save when required fields missing', async () => {
    render(<AcquisitionRationaleForm catalogItemId={5} onSaved={() => {}} />)
    const saveBtn = await screen.findByRole('button', { name: /Save rationale/i })
    expect(saveBtn).toBeDisabled()
  })

  it('submits valid form via createRationale', async () => {
    const { createRationale } = await import('@/api/acquisitionRationale')
    const onSaved = vi.fn()
    render(<AcquisitionRationaleForm catalogItemId={5} onSaved={onSaved} />)

    fireEvent.change(await screen.findByLabelText(/What prompted this acquisition\?/i), {
      target: { value: 'gap_in_collection' },
    })
    fireEvent.change(screen.getByLabelText(/Primary use case/i), {
      target: { value: 'new_parent' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Save rationale/i }))

    await waitFor(() => {
      expect(createRationale).toHaveBeenCalledWith(
        5,
        expect.objectContaining({
          signal_type: 'gap_in_collection',
          primary_use_case_slug: 'new_parent',
          weeding_condition: 'current_5yr',
        }),
      )
      expect(onSaved).toHaveBeenCalled()
    })
  })

  it('shows acknowledge checkbox only when anticipated challenges selected', async () => {
    render(<AcquisitionRationaleForm catalogItemId={5} onSaved={() => {}} />)
    await screen.findByLabelText(/What prompted this acquisition\?/i)
    expect(screen.queryByLabelText(/anticipated this could be challenged/i)).toBeNull()
    const lgbtqCheckbox = screen.getByLabelText('LGBTQ+ Content')
    fireEvent.click(lgbtqCheckbox)
    expect(
      await screen.findByLabelText(/anticipated this could be challenged/i),
    ).toBeInTheDocument()
  })

  it('shows public summary input only when patron_visible toggled', async () => {
    render(<AcquisitionRationaleForm catalogItemId={5} onSaved={() => {}} />)
    await screen.findByLabelText(/What prompted this acquisition\?/i)
    expect(screen.queryByLabelText(/^Public summary/i)).toBeNull()
    fireEvent.click(screen.getByLabelText(/Show this rationale to patrons/i))
    expect(await screen.findByLabelText(/^Public summary/i)).toBeInTheDocument()
  })

  it('loads existing rationale in edit mode', async () => {
    const { getRationale } = await import('@/api/acquisitionRationale')
    ;(getRationale as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      id: 1,
      catalog_item_id: 5,
      signal_type: 'community_request',
      signal_ref_table: null,
      signal_ref_id: null,
      signal_note: 'community request from neighborhood',
      policy_clause: 'CDP-3.2',
      primary_use_case_slug: 'grief_loss',
      secondary_use_case_slugs: [],
      weeding_condition: 'foundational_indefinite',
      weeding_signal_note: null,
      anticipated_challenge_reasons: [],
      anticipated_challenge_acknowledged: false,
      patron_visible: false,
      public_summary: null,
      created_at: '',
      updated_at: '',
      created_by_id: null,
    })
    render(<AcquisitionRationaleForm catalogItemId={5} onSaved={() => {}} mode="edit" />)
    const signalSelect = (await screen.findByLabelText(
      /What prompted this acquisition\?/i,
    )) as HTMLSelectElement
    await waitFor(() => expect(signalSelect.value).toBe('community_request'))
  })
})
