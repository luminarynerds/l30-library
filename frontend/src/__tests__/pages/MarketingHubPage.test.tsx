/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeAll } from 'vitest'
import '@testing-library/jest-dom'
import { screen, within, fireEvent } from '@testing-library/react'
import { render } from '../utils/test-utils'

// Preload English translations so tab labels (marketingHub.tab*) resolve.

// Override the global AuthContext mock from setup.ts so the page passes its
// role check and renders the tablist.
vi.mock('@/contexts/AuthContext', async () => {
  const React = await import('react')
  const staffAuth = {
    user: {
      id: 1,
      email: 'staff@example.org',
      role: 'staff' as const,
      is_active: true,
      is_board_member: false,
    },
    token: 'mock-staff-token',
    isLoading: false,
    isAuthenticated: true,
    sessionExpired: false,
    clearSessionExpired: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    updateProfile: vi.fn(),
    refreshUser: vi.fn(),
    showTimeoutWarning: false,
    timeoutSeconds: 120,
    dismissTimeoutWarning: vi.fn(),
    extendSession: vi.fn(),
    getSessionDuration: vi.fn(() => null),
  }
  return {
    AuthProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement(React.Fragment, null, children),
    useAuth: () => staffAuth,
    default: staffAuth,
  }
})

// Mock StaffLayout to a passthrough so we don't pull in the sidebar/branding chain.
vi.mock('@/components/staff/StaffLayout', () => ({
  StaffLayout: ({ children, title }: { children: React.ReactNode; title?: string }) => (
    <div data-testid="staff-layout" data-title={title}>{children}</div>
  ),
}))

// Mock the heavy tab panel children — they fetch via tanstack-query and aren't
// what this suite is testing. The Directory tab is hand-rolled inside the page
// itself, so no mock is needed for it.
vi.mock('@/components/marketing-hub/StatsHeader', () => ({
  default: () => <div data-testid="stats-header" />,
}))
vi.mock('@/components/marketing-hub/HistoryTab', () => ({
  HistoryTab: () => <div data-testid="history-tab" />,
}))
vi.mock('@/components/marketing-hub/AnalyticsTab', () => ({
  AnalyticsTab: () => <div data-testid="analytics-tab" />,
}))
vi.mock('@/components/marketing/AIContentGenerator', () => ({
  default: () => <div data-testid="ai-generator" />,
}))

// Feature flag harness — switched per test via mockFeatures.* below.
const mockFeatures = vi.hoisted(() => ({
  ai_tools_enabled: true,
  outreach_enabled: true,
  marketing_enabled: true,
}))
vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({
    features: null,
    loading: false,
    refetch: vi.fn(),
    isFeatureEnabled: (name: string) =>
      (mockFeatures as Record<string, boolean>)[name] ?? true,
  }),
  OrganizationFeaturesProvider: ({ children }: { children: React.ReactNode }) =>
    children,
}))

import MarketingHubPage from '@/pages/MarketingHubPage'

function getTablist() {
  return screen.getByRole('tablist', { name: /Marketing Hub sections/i })
}

describe('MarketingHubPage', () => {
  beforeAll(() => {
    // reset to defaults for each describe-block run
    mockFeatures.ai_tools_enabled = true
    mockFeatures.outreach_enabled = true
    mockFeatures.marketing_enabled = true
  })

  it('renders 4 tabs in the canonical order with ARIA roles when all flags are on', () => {
    mockFeatures.ai_tools_enabled = true
    mockFeatures.outreach_enabled = true

    render(<MarketingHubPage />)

    const tablist = getTablist()
    const tabs = within(tablist).getAllByRole('tab')
    expect(tabs).toHaveLength(4)
    expect(tabs.map((t) => t.textContent?.trim())).toEqual([
      'Create',
      'History',
      'Analytics',
      'Directory',
    ])

    // First tab is initially selected (Create).
    expect(tabs[0]).toHaveAttribute('aria-selected', 'true')
    expect(tabs[1]).toHaveAttribute('aria-selected', 'false')

    // tabpanel exists and references the active tab.
    const panel = screen.getByRole('tabpanel')
    expect(panel.id).toBe(tabs[0]?.getAttribute('aria-controls'))
  })

  it('renders the Directory panel with every expected link when flags are on', () => {
    mockFeatures.ai_tools_enabled = true
    mockFeatures.outreach_enabled = true

    render(<MarketingHubPage />)

    // Activate Directory tab.
    fireEvent.click(screen.getByRole('tab', { name: /Directory/i }))

    const panel = screen.getByRole('tabpanel')

    // Every directory link preserved from the old MarketingHubNavigationPage,
    // except the self-referential "Marketing Hub" entry (dropped intentionally).
    const expectedLinks: Array<[string, string]> = [
      ['Interest Categories', '/staff/marketing'],
      ['Outreach', '/staff/outreach'],
      ['Social Sharing', '/staff/admin/social-sharing'],
      ['Sharing Analytics', '/staff/admin/analytics/sharing'],
      ['Journey Analytics', '/staff/admin/analytics/journeys'],
    ]
    for (const [label, href] of expectedLinks) {
      const link = within(panel).getByRole('link', { name: new RegExp(label, 'i') })
      expect(link).toHaveAttribute('href', href)
    }

    // Both category headings present.
    expect(within(panel).getByText('Outreach', { selector: 'h2' })).toBeInTheDocument()
    expect(within(panel).getByText('Analytics', { selector: 'h2' })).toBeInTheDocument()
  })

  it('hides outreach-gated directory links when outreach_enabled is false', () => {
    mockFeatures.ai_tools_enabled = true
    mockFeatures.outreach_enabled = false

    render(<MarketingHubPage />)
    fireEvent.click(screen.getByRole('tab', { name: /Directory/i }))

    const panel = screen.getByRole('tabpanel')

    // outreach-gated links are gone.
    expect(within(panel).queryByRole('link', { name: /Outreach/i })).toBeNull()
    expect(within(panel).queryByRole('link', { name: /Journey Analytics/i })).toBeNull()
    // Outreach-gated "Interest Categories" link is also gone.
    expect(within(panel).queryByRole('link', { name: /Interest Categories/i })).toBeNull()

    // Non-gated links survive.
    expect(within(panel).getByRole('link', { name: /Social Sharing/i })).toHaveAttribute(
      'href',
      '/staff/admin/social-sharing',
    )
    expect(within(panel).getByRole('link', { name: /Sharing Analytics/i })).toHaveAttribute(
      'href',
      '/staff/admin/analytics/sharing',
    )
  })

  it('hides Create/History tabs and defaults to Directory when ai_tools_enabled is false', () => {
    mockFeatures.ai_tools_enabled = false
    mockFeatures.outreach_enabled = true

    render(<MarketingHubPage />)

    const tablist = getTablist()
    const tabs = within(tablist).getAllByRole('tab')
    expect(tabs.map((t) => t.textContent?.trim())).toEqual([
      'Analytics',
      'Directory',
    ])

    // Directory should be selected when AI is off (no Create surface available).
    const directoryTab = within(tablist).getByRole('tab', { name: /Directory/i })
    expect(directoryTab).toHaveAttribute('aria-selected', 'true')

    // Directory panel renders.
    const panel = screen.getByRole('tabpanel')
    expect(within(panel).getByRole('link', { name: /Sharing Analytics/i })).toBeInTheDocument()
  })
})
