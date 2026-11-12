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
vi.mock('@/components/knowledge-base/KnowledgeBaseSearch', () => ({ default: () => null }))
vi.mock('@/api/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: [] }),
  },
}))

import { render } from '@/__tests__/utils/test-utils'
import { screen } from '@testing-library/react'
import StaffKnowledgeBase from '@/pages/StaffKnowledgeBase'

describe('StaffKnowledgeBase section nav', () => {
  it('renders a tablist that does not use horizontal overflow scrolling', async () => {
    render(<StaffKnowledgeBase />)
    const tablist = await screen.findByRole('tablist', { name: /knowledge base sections/i })
    expect(tablist.className).not.toMatch(/overflow-x-auto/)
    expect(tablist.className).toMatch(/flex-wrap/)
  })

  it('reads the initial section from the ?section= query param', async () => {
    render(<StaffKnowledgeBase />, {
      routerProps: { initialEntries: ['/staff/knowledge-base?section=articles'] },
    })
    const tab = await screen.findByRole('tab', { name: /articles & policies/i })
    expect(tab).toHaveAttribute('aria-selected', 'true')
  })
})
