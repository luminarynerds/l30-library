/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import StaffPositivityHubPage, { summarizePositivity } from '../../pages/StaffPositivityHubPage'

// Mock i18n so t() returns its key (or last segment) deterministically.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}))

// Mock the AdminShell — it pulls Auth/Layout context we don't need here.
vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div data-testid="admin-shell" data-title={title}>{children}</div>
  ),
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

vi.mock('../../api/staff-positivity-api', () => ({
  createPositivityEntry: vi.fn(),
  listPositivityEntries: vi.fn().mockResolvedValue({ entries: [], total: 0 }),
  getPositivityDigest: vi.fn().mockResolvedValue({
    feedback: 0, win: 0, program: 0, thank_you: 0, compliment: 0,
    story: 0, appreciation: 0, total: 0, advocacy_flagged: 0,
    patron_submissions: 0, pending_moderation: 0,
  }),
  deletePositivityEntry: vi.fn(),
  toggleAdvocacyFlag: vi.fn(),
  getAdvocacyEntries: vi.fn().mockResolvedValue({ entries: [], count: 0 }),
  getModerationQueue: vi.fn().mockResolvedValue({ entries: [], total: 0 }),
  moderateEntry: vi.fn(),
}))

describe('summarizePositivity', () => {
  it('returns empty state when no complaints and no praise are logged', () => {
    const r = summarizePositivity(0, 0)
    expect(r.praiseCount).toBe(0)
    expect(r.ratioLabel).toBe('No entries yet')
  })

  it('returns all-praise state when no complaints are logged', () => {
    const r = summarizePositivity(5, 0)
    expect(r.praiseCount).toBe(5)
    expect(r.ratioLabel).toBe('All praise this month')
  })

  it('calculates praise-to-complaint ratio for balanced tracking', () => {
    const r = summarizePositivity(3, 2)
    expect(r.praiseCount).toBe(3)
    expect(r.ratioLabel).toBe('1.5:1 praise-to-complaint')
  })
})

describe('StaffPositivityHubPage tab ARIA + keyboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  async function renderHub() {
    const result = render(<StaffPositivityHubPage />)
    // Wait for initial data load to settle.
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /Joy Board/i })).toBeInTheDocument()
    })
    return result
  }

  it('exposes a tablist with three tabs and proper aria-selected', async () => {
    await renderHub()

    const tablist = screen.getByRole('tablist', { name: /Positivity Hub sections/i })
    expect(tablist).toBeInTheDocument()

    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(3)

    const joy = screen.getByRole('tab', { name: /Joy Board/i })
    const mod = screen.getByRole('tab', { name: /Moderation/i })
    const adv = screen.getByRole('tab', { name: /Advocacy/i })

    expect(joy).toHaveAttribute('aria-selected', 'true')
    expect(mod).toHaveAttribute('aria-selected', 'false')
    expect(adv).toHaveAttribute('aria-selected', 'false')

    // Roving tabindex: only active is 0.
    expect(joy).toHaveAttribute('tabindex', '0')
    expect(mod).toHaveAttribute('tabindex', '-1')
    expect(adv).toHaveAttribute('tabindex', '-1')
  })

  it('wires aria-controls to a matching tabpanel id, and tabpanel labelled by tab', async () => {
    await renderHub()

    const joy = screen.getByRole('tab', { name: /Joy Board/i })
    const panelId = joy.getAttribute('aria-controls')!
    expect(panelId).toBeTruthy()

    const panel = document.getElementById(panelId)
    expect(panel).not.toBeNull()
    expect(panel).toHaveAttribute('role', 'tabpanel')
    expect(panel).toHaveAttribute('aria-labelledby', joy.id)
    expect(panel).toHaveAttribute('tabindex', '0')
  })

  it('ArrowRight moves focus and activates next tab; ArrowLeft wraps backward', async () => {
    const user = userEvent.setup()
    await renderHub()

    const joy = screen.getByRole('tab', { name: /Joy Board/i })
    joy.focus()
    expect(joy).toHaveFocus()

    await user.keyboard('{ArrowRight}')
    const mod = screen.getByRole('tab', { name: /Moderation/i })
    await waitFor(() => {
      expect(mod).toHaveAttribute('aria-selected', 'true')
      expect(mod).toHaveFocus()
    })

    await user.keyboard('{ArrowLeft}')
    await waitFor(() => {
      expect(joy).toHaveAttribute('aria-selected', 'true')
      expect(joy).toHaveFocus()
    })

    // Wrap backward from first.
    await user.keyboard('{ArrowLeft}')
    const adv = screen.getByRole('tab', { name: /Advocacy/i })
    await waitFor(() => {
      expect(adv).toHaveAttribute('aria-selected', 'true')
    })
  })

  it('Home jumps to first tab, End jumps to last tab', async () => {
    const user = userEvent.setup()
    await renderHub()

    const joy = screen.getByRole('tab', { name: /Joy Board/i })
    const adv = screen.getByRole('tab', { name: /Advocacy/i })

    joy.focus()
    await user.keyboard('{End}')
    await waitFor(() => {
      expect(adv).toHaveAttribute('aria-selected', 'true')
      expect(adv).toHaveFocus()
    })

    await user.keyboard('{Home}')
    await waitFor(() => {
      expect(joy).toHaveAttribute('aria-selected', 'true')
      expect(joy).toHaveFocus()
    })
  })

  it('clicking a tab updates aria-selected and shows the matching panel', async () => {
    const user = userEvent.setup()
    await renderHub()

    const adv = screen.getByRole('tab', { name: /Advocacy/i })
    await user.click(adv)

    await waitFor(() => {
      expect(adv).toHaveAttribute('aria-selected', 'true')
    })

    const panelId = adv.getAttribute('aria-controls')!
    const panel = document.getElementById(panelId)
    expect(panel).toHaveAttribute('aria-labelledby', adv.id)
  })
})
