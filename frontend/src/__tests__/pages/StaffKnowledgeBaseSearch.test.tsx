/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { vi } from 'vitest'

// AdminShell renders StaffLayout which has deep auth/nav dependencies; stub it.
vi.mock('@/components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

// Stub child panels so they don't fire real API calls.
vi.mock('@/components/knowledge-base/QuickAnswers', () => ({ default: () => <div data-testid="panel-quick-answers" /> }))
vi.mock('@/components/knowledge-base/ArticleList', () => ({ default: () => <div data-testid="panel-articles" /> }))
vi.mock('@/components/knowledge-base/DecisionTreeBrowser', () => ({ default: () => <div data-testid="panel-decision-trees" /> }))
vi.mock('@/components/knowledge-base/VideoTutorials', () => ({ default: () => <div data-testid="panel-videos" /> }))
vi.mock('@/components/knowledge-base/OnboardingChecklist', () => ({ default: () => <div data-testid="panel-onboarding" /> }))
vi.mock('@/components/knowledge-base/StaffQA', () => ({ default: () => <div data-testid="panel-qa" /> }))
vi.mock('@/components/knowledge-base/BookmarkedArticles', () => ({ default: () => <div data-testid="panel-bookmarks" /> }))
vi.mock('@/components/knowledge-base/ContentFlagsReview', () => ({ default: () => <div data-testid="panel-flags" /> }))
// KnowledgeBaseSearch is NOT mocked here — we need it to render for search tests.
vi.mock('@/api/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: [] }),
  },
}))

import { render, screen, userEvent } from '@/__tests__/utils/test-utils'
import StaffKnowledgeBase from '@/pages/StaffKnowledgeBase'

describe('StaffKnowledgeBase persistent search', () => {
  it('shows a search bar regardless of active section', async () => {
    render(<StaffKnowledgeBase />, {
      routerProps: { initialEntries: ['/staff/knowledge-base?section=videos'] },
    })
    expect(await screen.findByRole('searchbox', { name: /search the knowledge base/i })).toBeInTheDocument()
  })

  it('switches to the Articles section when a search is submitted', async () => {
    const user = userEvent.setup()
    render(<StaffKnowledgeBase />, {
      routerProps: { initialEntries: ['/staff/knowledge-base?section=videos'] },
    })
    const box = await screen.findByRole('searchbox', { name: /search the knowledge base/i })
    await user.type(box, 'overdue fine{Enter}')
    const articlesTab = await screen.findByRole('tab', { name: /articles & policies/i })
    expect(articlesTab).toHaveAttribute('aria-selected', 'true')
  })

  it('hides the persistent search bar on the quick-answers tab (default)', () => {
    render(<StaffKnowledgeBase />, {
      routerProps: { initialEntries: ['/staff/knowledge-base'] },
    })
    expect(screen.queryByRole('searchbox', { name: /search the knowledge base/i })).toBeNull()
  })

  it('shows the persistent search bar on the articles tab', async () => {
    render(<StaffKnowledgeBase />, {
      routerProps: { initialEntries: ['/staff/knowledge-base?section=articles'] },
    })
    expect(await screen.findByRole('searchbox', { name: /search the knowledge base/i })).toBeInTheDocument()
  })
})
