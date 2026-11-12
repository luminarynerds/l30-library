/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import { SimilarRationalesPanel } from '@/components/cataloging/SimilarRationalesPanel'

const STRINGS: Record<string, string> = {
  'acquisitionRationale.similar.title': 'Similar past rationales',
  'acquisitionRationale.similar.searching': 'Searching past rationales...',
  'acquisitionRationale.similar.empty':
    'No similar rationales yet -- this looks like a new collecting direction.',
  'acquisitionRationale.similar.primaryUseCase': 'Primary use: {{slug}}',
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
  findSimilarRationales: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('SimilarRationalesPanel', () => {
  it('renders hits when API returns them', async () => {
    const { findSimilarRationales } = await import('@/api/acquisitionRationale')
    ;(findSimilarRationales as ReturnType<typeof vi.fn>).mockResolvedValue({
      query: 'cyber thrillers for commute readers',
      hits: [
        {
          // Structured-metadata path: primary_use_case comes from metadata.
          aku_id: 'rationale-1',
          title: 'Acquisition rationale: Cyber Thriller A',
          body: 'Bought because patrons keep asking.',
          tags: ['rationale', 'meta:primary_use_case:commute'],
          metadata: { primary_use_case: 'commute' },
          score: 0.91,
        },
        {
          // Tag-prefix fallback path: metadata absent, slug derived from tag.
          aku_id: 'rationale-2',
          title: 'Acquisition rationale: Cyber Thriller B',
          body: 'Gap in collection identified.',
          tags: ['rationale', 'meta:primary_use_case:bedtime'],
          score: 0.83,
        },
      ],
    })

    render(<SimilarRationalesPanel query="cyber thrillers for commute readers" />)

    expect(
      await screen.findByText(/Acquisition rationale: Cyber Thriller A/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Acquisition rationale: Cyber Thriller B/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/Primary use: commute/i)).toBeInTheDocument()
    expect(screen.getByText(/Primary use: bedtime/i)).toBeInTheDocument()
    expect(findSimilarRationales).toHaveBeenCalledWith(
      'cyber thrillers for commute readers',
    )
  })

  it('renders empty state when hits=[]', async () => {
    const { findSimilarRationales } = await import('@/api/acquisitionRationale')
    ;(findSimilarRationales as ReturnType<typeof vi.fn>).mockResolvedValue({
      query: 'novel collecting direction here',
      hits: [],
    })

    render(<SimilarRationalesPanel query="novel collecting direction here" />)

    expect(
      await screen.findByText(/No similar rationales yet/i),
    ).toBeInTheDocument()
  })

  it('does not call API when query is too short (<8 chars)', async () => {
    const { findSimilarRationales } = await import('@/api/acquisitionRationale')

    const { container } = render(<SimilarRationalesPanel query="short" />)

    // Wait past the debounce window to be sure no call would fire.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 400))
    })

    expect(findSimilarRationales).not.toHaveBeenCalled()
    // Panel hides itself entirely when query is too short.
    expect(container.firstChild).toBeNull()
  })

  it('renders empty (no crash) when query becomes empty after being long', async () => {
    const { findSimilarRationales } = await import('@/api/acquisitionRationale')
    ;(findSimilarRationales as ReturnType<typeof vi.fn>).mockResolvedValue({
      query: '',
      hits: [],
    })

    const { rerender, container } = render(
      <SimilarRationalesPanel query="long enough query" />,
    )
    await waitFor(() => expect(findSimilarRationales).toHaveBeenCalled())

    rerender(<SimilarRationalesPanel query="" />)
    await waitFor(() => expect(container.firstChild).toBeNull())
  })
})
